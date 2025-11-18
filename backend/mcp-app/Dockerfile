# 使用Python 3.11作为基础镜像
FROM python:3.11.7-slim

# 配置 Debian 镜像源（清华大学镜像源）
# RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
#     echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 或者使用官方源作为备用（如果镜像源有问题，请取消注释下面几行）
RUN echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list && \
echo "deb http://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
echo "deb http://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 创建非root用户以提高安全性
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 复制依赖文件
COPY requirements.txt .

# 更新 pip 并配置镜像源（CERNET 中国教育和科研计算机网）
RUN pip config set global.index-url "https://mirrors.cernet.edu.cn/pypi/web/simple" && \
    pip config set global.trusted-host "mirrors.cernet.edu.cn"
RUN pip install --upgrade pip setuptools wheel

# 安装Python依赖（全局已配置镜像源）
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录并设置权限
RUN mkdir -p /app/logs /app/configs && \
    chown -R mcpuser:mcpuser /app && \
    chmod -R 755 /app && \
    chmod 777 /app/configs /app/logs

# 切换到非root用户
USER mcpuser

# 暴露端口
EXPOSE 8000

# 添加标签用于服务识别
LABEL service.name="mcp-service" \
      service.version="1.0.0" \
      service.description="MCP Base Service for tool management" \
      maintainer="your-email@example.com"

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
