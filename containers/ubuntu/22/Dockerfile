# Ubuntu 22.04 with systemd for Ansible Molecule testing
# Supports both amd64 and arm64 architectures

FROM ubuntu:22.04

LABEL maintainer="Herman Wong"
LABEL description="Ubuntu 22.04 with systemd for Ansible Molecule testing"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install systemd and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        systemd \
        systemd-sysv \
        dbus \
        python3.11 \
        python3-pip \
        sudo \
        openssh-server \
        openssh-client \
        openssl \
        wget \
        curl \
        tar \
        gzip \
        unzip \
        netcat-openbsd \
        net-tools \
        procps \
        iproute2 \
        hostname \
        ca-certificates \
        gnupg \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Configure systemd
# Remove unnecessary systemd services
RUN (cd /lib/systemd/system/sysinit.target.wants/ && \
    for i in *; do \
        [ "$i" = "systemd-tmpfiles-setup.service" ] || rm -f "$i"; \
    done); \
    rm -f /lib/systemd/system/multi-user.target.wants/*; \
    rm -f /etc/systemd/system/*.wants/*; \
    rm -f /lib/systemd/system/local-fs.target.wants/*; \
    rm -f /lib/systemd/system/sockets.target.wants/*udev*; \
    rm -f /lib/systemd/system/sockets.target.wants/*initctl*; \
    rm -f /lib/systemd/system/basic.target.wants/*; \
    rm -f /lib/systemd/system/anaconda.target.wants/* 2>/dev/null || true

# Create ansible user with sudo access
RUN useradd -m -s /bin/bash ansible && \
    echo "ansible ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/ansible && \
    chmod 0440 /etc/sudoers.d/ansible

# Configure SSH
RUN mkdir -p /run/sshd && \
    ssh-keygen -A

# Set up volumes for systemd
VOLUME ["/sys/fs/cgroup", "/tmp", "/run"]

# Expose SSH port
EXPOSE 22

# Set the init system as entrypoint
STOPSIGNAL SIGRTMIN+3
CMD ["/lib/systemd/systemd"]
