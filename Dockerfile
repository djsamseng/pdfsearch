# Define function directory
ARG LAMBDA_TASK_ROOT="/var/task"
ARG FUNCTION_DIR="${LAMBDA_TASK_ROOT}"

FROM python:3.8 as build-image

# Install aws-lambda-cpp build dependencies
RUN apt-get update && \
  apt-get install -y \
  g++ \
  make \
  cmake \
  unzip \
  libcurl4-openssl-dev

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Create function directory
RUN mkdir -p ${FUNCTION_DIR}

# Install the runtime interface client
RUN pip install \
        --target ${FUNCTION_DIR} \
        awslambdaric

# Multi-stage build: grab a fresh copy of the base image
FROM python:3.8

# Include global arg in this stage of the build
ARG FUNCTION_DIR
# Set working directory to function root directory
WORKDIR ${FUNCTION_DIR}

# Copy in the build image dependencies
COPY --from=build-image ${FUNCTION_DIR} ${FUNCTION_DIR}

COPY ./entry_script.sh /entry_script.sh
ADD bin/aws-lambda-rie-x86_64 /usr/local/bin/aws-lambda-rie
ENTRYPOINT [ "/entry_script.sh" ]
ARG LAMBDA_TASK_ROOT



#FROM public.ecr.aws/lambda/python:3.8
# RUN yum update && yum install -y git
RUN apt-get update && apt-get install -y git
COPY lambdacontainer/processpdffunction/requirements.txt .
RUN pip3 install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"
# https://github.com/supabase-community/supabase-py/issues/33
RUN pip3 uninstall dataclasses -y
RUN rm -rf ${LAMBDA_TASK_ROOT}/dataclasses*

COPY lambdacontainer/processpdffunction/app.py ${LAMBDA_TASK_ROOT}
COPY lambdacontainer/processpdffunction/*.py ${LAMBDA_TASK_ROOT}
ADD lambdacontainer/processpdffunction/pdfextract ${LAMBDA_TASK_ROOT}/pdfextract/

COPY lambdacontainer/processpdffunction/symbols_michael_smith.json ${LAMBDA_TASK_ROOT}
# Remove below for production
COPY plan.pdf ${LAMBDA_TASK_ROOT}

RUN echo "Update pdfminer to not analyze"
RUN exit 1;

CMD [ "app.handler" ]