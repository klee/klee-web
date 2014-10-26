FROM ubuntu:14.04
RUN apt-get -y update && apt-get -y upgrade

#Install dependencies
RUN apt-get -y install g++ curl dejagnu subversion bison flex bc libcap-dev wget git cmake git patch python-minimal libboost-all-dev ncurses-dev

ENV C_INCLUDE_PATH /usr/include/x86_64-linux-gnu
ENV CPLUS_INCLUDE_PATH /usr/include/x86_64-linux-gnu
ENV PATH $PATH:/src/llvm-gcc4.2-2.9-x86_64-linux/bin

RUN mkdir /src && cd /src && \
    wget http://llvm.org/releases/2.9/llvm-gcc4.2-2.9-x86_64-linux.tar.bz2 && \
    tar -jxvf llvm-gcc4.2-2.9-x86_64-linux.tar.bz2 && \
    rm /src/*.tar.bz2 && \
    cd /src  && \
    wget http://llvm.org/releases/2.9/llvm-2.9.tgz && \
    tar -zxvf llvm-2.9.tgz && rm *.tgz && \
    cd /src/llvm-2.9 && \
    wget https://gist.githubusercontent.com/ilovepjs/55a8d84000cc5d23a48c/raw/a992a62eaab5600994c66a6d42b6eeec80149cdd/llvm_patch && \
    patch -p1 < llvm_patch && \
    ./configure --enable-optimized --disable-assertions --enable-targets=host-only && \
    make -j `nproc` && \
    rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/man && \
    rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/share && \
    rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/info && \
    cd /src  && \
    git clone https://github.com/stp/stp.git && \
    cd /src/stp && \
    mkdir build && cd build && \
    cmake -G 'Unix Makefiles' /src/stp && \
    make && sudo make install && \
    sudo ldconfig && ulimit -s unlimited && \
    cd /src  && \
    git clone --depth 1 --branch klee_0_9_29 https://github.com/klee/klee-uclibc.git && \
    cd /src/klee-uclibc/ && \
    ./configure --with-llvm-config /src/llvm-2.9/Release/bin/llvm-config --make-llvm-lib && \
    make -j`nproc` && \
    cd /src && git clone https://github.com/klee/klee.git && \
    cd /src/klee && \
    ./configure --enable-posix-runtime --with-stp=/usr/local --with-llvm=/src/llvm-2.9/ --with-uclibc=/src/klee-uclibc/ && \
    make ENABLE_OPTIMIZED=1 && \
    rm -rf /src/klee-uclibc && \
    rm -rf /src/stp && \
    rm -rf /src/klee/examples && \
    rm -rf /src/klee/autoconf && \
    rm -rf /src/klee/docs && \
    rm -rf /src/klee/lib && \
    rm -rf /src/klee/runtime && \
    rm -rf /src/klee/scripts && \
    rm -rf /src/klee/test && \
    rm -rf /src/klee/tools && \
    rm -rf /src/klee/unittests && \
    rm -rf /src/klee/utils && \
    rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/lib32 && \
    rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/include && \
    rm -rf /src/llvm-2.9 && \
    make check  && \
    make test && \
    make unittests && \
    sudo make install && \
    cd /root
