import os
import shutil

# --- 核心修改：设置 Hugging Face 镜像环境变量 ---
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 1. 导入所需工具
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from zhipuai import ZhipuAI

# 2. 配置参数
PDF_PATH = "C:/Users/Administrator/Desktop/1.pdf"  # ⚠️ 请修改为你的PDF路径
EMBEDDING_MODEL = "moka-ai/m3e-base"
CHROMA_DB_PATH = "./my_chroma_db"  # ChromaDB 数据持久化文件夹
COLLECTION_NAME = "employee_handbook"

# --- 优化：增大切片和重叠 ---
CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 3

# --- 配置 API Key ---
api_key = os.getenv("GLM_API_KEY")
if not api_key:
    print("⚠️ 警告：未在环境变量中找到 GLM_API_KEY")
else:
    import ZhipuAI
    ZhipuAI.api_key = api_key

# 3. 提取PDF文本并分块
def extract_and_split_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    
    # --- 调试：打印读取到的文字长度 ---
    print(f"[调试] PDF读取结果：共读取到 {len(text)} 个字符")
    if len(text) < 50:
        print("⚠️ 警告：读取到的文字极少，可能是扫描版PDF！")
        
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len
    )
    chunks = text_splitter.split_text(text)
    return chunks

# 4. 自定义 Embedding 函数类 (用于让 ChromaDB 使用 m3e)
class M3EEmbeddingFunction:
    def __init__(self, model):
        self.model = model
    def __call__(self, input):
        # input 是文本列表
        # convert_to_numpy=True 确保返回 numpy 数组，然后转 list
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()

# 5. 检索相关片段
def retrieve_relevant_chunks(query, collection, model, top_k):
    # 1. 用 m3e 计算查询向量
    query_embedding = model.encode([query]).tolist()
    
    # 2. 查询
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "distances"]
    )
    
    # 3. 解析结果
    docs = results['documents'][0]
    dists = results['distances'][0]
    
    print(f"\n[调试] 检索到的距离: {dists}")
    
    relevant_chunks = []
    # --- 核心修复：大幅调大阈值 ---
    # m3e + L2 距离通常在 100-200 之间，之前的 1.5 太小了
    # 这里设为 500 确保能捞到数据
    threshold = 500.0 
    
    for doc, dist in zip(docs, dists):
        if dist < threshold: 
            relevant_chunks.append(doc)
            print(f"   ✅ 命中距离 {dist:.2f}: {doc[:40]}...")
        else:
            print(f"   ⚠️ 过滤距离 {dist:.2f}: {doc[:40]}...")
            
    return relevant_chunks

# 6. 结合大模型生成答案
def generate_answer(query, relevant_chunks):
    if not relevant_chunks:
        return "根据提供的资料，无法回答该问题（检索结果为空）。"

    prompt = f"""你是一个严谨的文档问答助手。
请**严格仅依据**下方的【参考资料】来回答【问题】。

【参考资料】：
{chr(10).join(relevant_chunks)}

【回答规则】：
1. 必须在【参考资料】中找到依据才能回答。
2. 如果【参考资料】中没有包含答案，请直接回复：“根据提供的资料，无法回答该问题”。
3. **禁止**使用你预训练的外部知识，**禁止**编造。
4. 回答要简洁、客观。

【问题】：{query}
"""
    
    import dashscope
    from dashscope import Generation
    
    response = Generation.call(
        model='deepseek-v3', 
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=512,
        temperature=0
    )
    
    if response.status_code == 200:
        return response.output.choices[0].message.content
    else:
        return f"API调用失败: {response.code} - {response.message}"

# 7. 主函数
if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ 错误：找不到文件 '{PDF_PATH}'")
    else:
        # 1. 处理 PDF
        chunks = extract_and_split_pdf(PDF_PATH)
        
        if not chunks:
            print("❌ 错误：PDF 解析失败，没有获取到文本片段。")
        else:
            # 2. 加载模型
            print(f"正在加载模型 {EMBEDDING_MODEL}...")
            model = SentenceTransformer(EMBEDDING_MODEL)
            
            # 3. 初始化 ChromaDB
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            
            # 删除旧集合以重置 (确保每次运行都是新的)
            try: 
                client.delete_collection(COLLECTION_NAME)
                print(f"✅ 已清空旧数据库: {CHROMA_DB_PATH}")
            except: 
                pass
            
            # 创建新集合，使用自定义的 M3E 嵌入函数
            collection = client.create_collection(
                name=COLLECTION_NAME, 
                embedding_function=M3EEmbeddingFunction(model)
            )
            
            # 存入数据
            print(f"正在向数据库插入 {len(chunks)} 个片段...")
            collection.add(
                ids=[str(i) for i in range(len(chunks))],
                documents=chunks
            )
            print("✅ 向量数据库构建完成！")
            
            # 4. 问答循环
            print("\n--- 问答系统已启动 (输入 '退出' 结束) ---")
            
            while True:
                query = input("\n请输入你的问题：")
                if query == "退出":
                    print("问答结束，感谢使用～")
                    break
                
                # 检索
                relevant_chunks = retrieve_relevant_chunks(query, collection, model, TOP_K)
                
                # 调试打印
                print("-" * 30)
                if not relevant_chunks:
                    print("⚠️ [调试] 检索结果为空！(所有片段距离都超过阈值)")
                else:
                    print(f"✅ [调试] 成功检索到 {len(relevant_chunks)} 个有效片段")
                print("-" * 30)
                
                # 生成回答
                answer = generate_answer(query, relevant_chunks)
                print(f"\n答案：{answer}")