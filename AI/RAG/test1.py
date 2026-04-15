import os
import shutil

# --- 核心修改：设置 Hugging Face 镜像环境变量 ---
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 1. 导入所需工具
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import chromadb
from zhipuai import ZhipuAI

# 2. 配置参数
PDF_PATH = "C:/Users/Administrator/Desktop/1.pdf"
EMBEDDING_MODEL = "moka-ai/m3e-base"
CHROMA_DB_PATH = "./my_chroma_db"
COLLECTION_NAME = "employee_handbook"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200
TOP_K = 3

# 读取环境变量密钥
ZHIPU_API_KEY = os.getenv("GLM_API_KEY")
if not ZHIPU_API_KEY:
    raise ValueError("❌ 环境变量 GLM_API_KEY 未配置，请检查系统环境变量！")
client = ZhipuAI(api_key=ZHIPU_API_KEY)

# 3. 提取PDF文本
def extract_and_split_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    
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

# 4. ✅ 修复：自定义嵌入函数，添加 name() 方法（解决报错核心）
class M3EEmbeddingFunction:
    def __init__(self, model):
        self.model = model
    # 必须添加这个方法！兼容新版 ChromaDB
    def name(self):
        return "m3e_embedding_function"
    def __call__(self, input):
        embeddings = self.model.encode(input, convert_to_numpy=True)
        return embeddings.tolist()

# 5. 检索函数
def retrieve_relevant_chunks(query, collection, model, top_k):
    query_embedding = model.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "distances"]
    )
    
    docs = results['documents'][0]
    dists = results['distances'][0]
    
    print(f"\n[调试] 检索到的距离: {dists}")
    
    relevant_chunks = []
    threshold = 500.0 
    
    for doc, dist in zip(docs, dists):
        if dist < threshold: 
            relevant_chunks.append(doc)
            print(f"   ✅ 命中距离 {dist:.2f}: {doc[:40]}...")
            
    return relevant_chunks

# 6. 智谱GLM生成回答
def generate_answer(query, relevant_chunks):
    if not relevant_chunks:
        return "根据提供的资料，无法回答该问题（检索结果为空）。"

    prompt = f"""你是一个严谨的文档问答助手。
请**严格仅依据**参考资料回答问题，禁止编造。

参考资料：
{chr(10).join(relevant_chunks)}

问题：{query}
回答：
"""
    
    response = client.chat.completions.create(
        model="glm-4.5-air",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512
    )
    
    return response.choices[0].message.content

# 7. 主函数
if __name__ == "__main__":
    if not os.path.exists(PDF_PATH):
        print(f"❌ 错误：找不到文件 '{PDF_PATH}'")
    else:
        chunks = extract_and_split_pdf(PDF_PATH)
        
        if not chunks:
            print("❌ 错误：PDF 解析失败")
        else:
            print(f"正在加载模型 {EMBEDDING_MODEL}...")
            model = SentenceTransformer(EMBEDDING_MODEL)
            
            client_db = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            
            # ✅ 修复：删除旧数据库+重新创建（彻底解决集合冲突）
            try:
                client_db.delete_collection(COLLECTION_NAME)
            except:
                pass
            
            # 创建新集合
            collection = client_db.create_collection(
                name=COLLECTION_NAME,
                embedding_function=M3EEmbeddingFunction(model)
            )
            
            # 插入数据
            collection.add(
                ids=[str(i) for i in range(len(chunks))],
                documents=chunks
            )
            print("✅ 向量数据库构建完成！")
            
            # 问答循环
            while True:
                query = input("\n请输入你的问题：")
                if query == "退出":
                    print("问答结束～")
                    break
                
                relevant_chunks = retrieve_relevant_chunks(query, collection, model, TOP_K)
                answer = generate_answer(query, relevant_chunks)
                print(f"\n答案：{answer}")