FROM python:3.14-slim-bookworm
COPY --from=docker.io/astral/uv:latest /uv /uvx /bin/
RUN DEBIAN_FRONTEND="noninteractive" apt update --fix-missing \
    && apt-get install --no-install-recommends -y \
        curl \
    && apt-get clean \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Make new user
RUN groupadd -r pubtrends-datasets && useradd -ms /bin/bash -g pubtrends-datasets user && usermod -aG sudo user

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

RUN mkdir -p /pubtrends-datasets
RUN chown --recursive user:root /pubtrends-datasets

USER user
# Installing the latest miniconda to get a version of sqlite newer than 3.50
RUN curl --location https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh --output ~/miniconda.sh \
    && /bin/bash ~/miniconda.sh -b \
    && rm ~/miniconda.sh
ENV PATH=/home/user/miniconda3/bin:$PATH
# Fix shell for conda
USER root
RUN ln -snf /bin/bash /bin/sh

USER user

WORKDIR /home/user
# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

RUN mkdir -p ~/.pubtrends-datasets/logs
COPY config.properties /home/user/.pubtrends-datasets/config.properties

# Test DB generation
COPY src/test/db/testgeometadb.sql /home/user/testgeometadb.sql
COPY scripts /home/user/scripts
RUN bash /home/user/scripts/create_test_sample.sh /home/user/testgeometadb.sql
RUN sed -i "s|^test_geometadb_path\\s*=\\s*.*|test_geometadb_path=/home/user/geodatasets/testgeometadb.sqlite|" /home/user/.pubtrends-datasets/config.properties

RUN mkdir -p ~/geodatasets/soft_files
RUN sed -i "s|^dataset_download_folder\\s*=\\s*.*|dataset_download_folder=/home/user/geodatasets/soft_files|" /home/user/.pubtrends-datasets/config.properties
