libraries = [
    "pygame"
    # "os",
    # "time",
    # "random",
    # "pandas",
    # "requests",
    # "bs4",  # BeautifulSoup 的导入名是 bs4
    # "urllib.parse"
]

# 用于映射导入名到实际包名（可选，主要用于显示更友好的名称）
friendly_names = {
    "bs4": "beautifulsoup4",
    "urllib.parse": "urllib (standard library)"
}

print(f"{'库名称':<20} | {'状态':<10} | {'详细信息'}")
print("-" * 50)

for lib in libraries:
    try:
        if lib == "urllib.parse":
            # urllib.parse 是标准库的一部分，不能直接 import urllib.parse 作为一个模块对象赋值给变量，
            # 但我们可以尝试 from urllib.parse import urljoin 来测试
            __import__(lib.split('.')[0]) # 先确保父模块存在
            exec(f"from {lib} import urljoin")
        else:
            __import__(lib)
        
        status = "✅ 成功"
        details = "-"
    except ImportError as e:
        status = "❌ 失败"
        details = str(e)
    
    display_name = friendly_names.get(lib, lib)
    print(f"{display_name:<20} | {status:<10} | {details}")