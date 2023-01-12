FROM public.ecr.aws/lambda/python:3.8
RUN yum update && yum install -y git
COPY lambdacontainer/processpdffunction/requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
# https://github.com/supabase-community/supabase-py/issues/33
RUN pip uninstall dataclasses -y
RUN rm -rf ${LAMBDA_TASK_ROOT}/dataclasses*

COPY lambdacontainer/processpdffunction/app.py ${LAMBDA_TASK_ROOT}
COPY lambdacontainer/processpdffunction/*.py ${LAMBDA_TASK_ROOT}
ADD pdfextract ${LAMBDA_TASK_ROOT}/pdfextract/

COPY lambdacontainer/processpdffunction/symbols_michael_smith.json ${LAMBDA_TASK_ROOT}
# Remove below for production
COPY plan.pdf ${LAMBDA_TASK_ROOT}

CMD [ "app.handler" ]