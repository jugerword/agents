FROM python:3.11-slim

COPY . /home
WORKDIR /home

# pysha3 does not build on Python 3.11 (upstream known issue); install the
# rest first, then eip712-structs without deps so poly_eip712_structs works.
RUN pip3 install -r requirements.txt || true
RUN pip3 install --no-deps eip712-structs==1.1.0

CMD ["python3", "scripts/python/cli.py"]
