FROM public.ecr.aws/lambda/python:3.8
RUN yum update && yum install -y git
COPY requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

COPY app.py ${LAMBDA_TASK_ROOT}
COPY *.py ${LAMBDA_TASK_ROOT}

COPY symbols_michael_smith.json ${LAMBDA_TASK_ROOT}
# Remove below for production
COPY plan.pdf ${LAMBDA_TASK_ROOT}

CMD [ "app.handler" ]