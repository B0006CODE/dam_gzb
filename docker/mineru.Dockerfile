# Lastest version: wget https://gcore.jsdelivr.net/gh/opendatalab/MinerU@master/docker/china/Dockerfile

# Use the official sglang image
FROM lmsysorg/sglang:v0.4.9.post3-cu126
# For blackwell GPU, use the following line instead:
# FROM lmsysorg/sglang:v0.4.9.post3-cu128-b200

# 使用清华镜像源加速下载
RUN sed -i 's|http://archive.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list && \
    sed -i 's|http://security.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list

# Install libgl for opencv support & Noto fonts for Chinese characters
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        fonts-noto-core \
        fonts-noto-cjk \
        fontconfig \
        libgl1 && \
    fc-cache -fv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install mineru with vLLM (required inference engine for mineru-openai-server)
RUN python3 -m pip install -U 'mineru[core]' vllm \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --break-system-packages \
    --retries 10 \
    --resume-retries 10 \
    --timeout 120 && \
    python3 -m pip cache purge

# Download models and update the configuration file
RUN /bin/bash -c "mineru-models-download -s modelscope -m all"

# Set the entry point to activate the virtual environment and run the command line tool
ENTRYPOINT ["/bin/bash", "-c", "export MINERU_MODEL_SOURCE=local && exec \"$@\"", "--"]