FROM hubdocker.aminer.cn/library/python-base:1.0.1

COPY devlop_home /app/devlop_home/
COPY py_devlop.sh /app/py_devlop.sh

# COPY devlop_data/input_param.json /app/devlop_data/input_param.json
# COPY devlop_data/questions /app/devlop_data/questions
# COPY devlop_result/output.json /app/devlop_result/answer.json

RUN pip install --no-cache-dir -r /app/devlop_home/requirements.txt && \
    rm -rf /root/.cache

ARG ZHIPUAI_API_KEY
ENV ZHIPUAI_API_KEY=${ZHIPUAI_API_KEY}

WORKDIR /app/
CMD ["/app/py_devlop.sh", "/app/devlop_data/input_param.json", "/app/devlop_result/answer.json" ]