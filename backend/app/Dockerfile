# 使用Python 3.11作为基础镜像
FROM python:3.11.7-slim

# 清理可能存在的旧配置，避免重复配置警告
RUN rm -f /etc/apt/sources.list.d/*.sources 2>/dev/null || true

# 方案1：使用更稳定的镜像源（清华大学镜像源）- 推荐国内使用
RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free non-free-firmware" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free non-free-firmware" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware" >> /etc/apt/sources.list

# 或者使用官方源作为备用（如果镜像源有问题，请取消注释下面几行，并注释掉上面的清华源）
# RUN echo "deb http://deb.debian.org/debian bookworm main" > /etc/apt/sources.list && \
#     echo "deb http://security.debian.org/debian-security bookworm-security main" >> /etc/apt/sources.list && \
#     echo "deb http://deb.debian.org/debian bookworm-updates main" >> /etc/apt/sources.list

# 安装必要的构建工具和依赖，增加错误处理和重试机制
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    -o Acquire::http::Timeout=60 \
    -o Acquire::http::Retries=5 \
    build-essential \
    python3-dev \
    make \
    libgl1 \
    libgl1-mesa-glx \
    libglu1-mesa \
    libglib2.0-0 \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 更新 pip 并配置镜像源（CERNET 中国教育和科研计算机网）
RUN pip config set global.index-url "https://mirrors.cernet.edu.cn/pypi/web/simple" && \
    pip config set global.trusted-host "mirrors.cernet.edu.cn"
RUN pip install --upgrade pip setuptools wheel

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 创建非root用户以提高安全性，并创建 home 目录
RUN groupadd -r appuser && \
    useradd -r -g appuser -m -d /home/appuser appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /home/appuser && \
    chmod 755 /home/appuser

# 拷贝依赖文件并安装
COPY requirements.txt /app/

# 使用 CERNET 源安装依赖，增加重试和超时（全局已配置镜像源）
RUN pip install --no-cache-dir \
    --timeout 1000 \
    --retries 10 \
    -r requirements.txt

# 拷贝代码
COPY . /app

# 创建必要的目录并设置权限
RUN mkdir -p /app/uploads /app/logs && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 8001



# 添加标签用于服务识别
LABEL service.name="main-app" \
      service.version="1.0.0" \
      service.description="主应用服务" \
      maintainer="your-email@example.com"

# 启动命令
CMD ["uvicorn", "app_main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
