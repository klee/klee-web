FROM ubuntu:14.04

ENV LLVM_VERSION 3.4
ENV DISABLE_ASSERTIONS 0
ENV ENABLE_OPTIMIZED 1

RUN apt-get update
RUN apt-get -y install g++ curl dejagnu bison flex bc libcap-dev wget cmake git python-minimal libboost-all-dev ncurses-dev wget unzip

RUN echo "deb http://llvm.org/apt/trusty/ llvm-toolchain-trusty-3.4 main" >> /etc/apt/sources.list.d/llvm.list
RUN echo "deb-src http://llvm.org/apt/trusty/ llvm-toolchain-trusty-3.4 main" >> /etc/apt/sources.list.d/llvm.list
RUN wget -O - http://llvm.org/apt/llvm-snapshot.gpg.key|sudo apt-key add -
RUN apt-get update

RUN apt-get install llvm-${LLVM_VERSION} llvm-${LLVM_VERSION}-dev clang-${LLVM_VERSION} lvm-${LLVM_VERSION}-tools -y
RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-3.4 20
RUN update-alternatives --install /usr/bin/clang++ clang++ /usr/bin/clang++-3.4 20

RUN mkdir /src && cd /src  && \
    git clone https://github.com/stp/stp.git && \
    cd /src/stp && \
    mkdir build && cd build && \
    cmake -G 'Unix Makefiles' /src/stp && \
    make -j `nproc` && sudo make install && \
    sudo ldconfig && ulimit -s unlimited && \
    cd /src  && \
    git clone --depth 1 --branch klee_0_9_29 https://github.com/klee/klee-uclibc.git && \
    cd /src/klee-uclibc/ && \
    ./configure --with-llvm-config /usr/bin/llvm-config-${LLVM_VERSION} --with-cc "/usr/bin/clang-${LLVM_VERSION}" --make-llvm-lib && \
    make -j `nproc` && \
	    cd /src && git clone https://github.com/klee/klee.git && \
    cd /src/klee && \
    git checkout 92c21e2d581bd7405032eaf67544611ccd30ab4e && \
    ./configure --enable-posix-runtime --with-stp=/usr/local --with-uclibc=/src/klee-uclibc/ \
    --with-llvmsrc=/usr/lib/llvm-${LLVM_VERSION}/build \
    --with-llvmobj=/usr/lib/llvm-${LLVM_VERSION}/build \
    --with-llvmcc=/usr/bin/clang-${LLVM_VERSION} \ 
    --with-llvmcxx=/usr/bin/clang++-${LLVM_VERSION} && \ 
    make -j `nproc` DISABLE_ASSERTIONS=${DISABLE_ASSERTIONS} ENABLE_OPTIMIZED=${ENABLE_OPTIMIZED} ENABLE_SHARED=0 && \
    make check  DISABLE_ASSERTIONS=${DISABLE_ASSERTIONS} ENABLE_OPTIMIZED=${ENABLE_OPTIMIZED} ENABLE_SHARED=0 && \
    make test DISABLE_ASSERTIONS=${DISABLE_ASSERTIONS} ENABLE_OPTIMIZED=${ENABLE_OPTIMIZED} ENABLE_SHARED=0 && \
    cd /src/ && \
    wget http://pkgs.fedoraproject.org/repo/pkgs/gtest/gtest-1.7.0.zip/2d6ec8ccdf5c46b05ba54a9fd1d130d7/gtest-1.7.0.zip && \
    unzip gtest-1.7.0.zip && \
    cd gtest-1.7.0/ && \
    cmake . && \
    make -j `nproc` && \
    cp lib* /usr/lib/ && \
    cp -r include/gtest /usr/include && \ 
    mkdir -p /usr/lib/llvm-${LLVM_VERSION}/build/unittests/ && \
    curl http://llvm.org/svn/llvm-project/llvm/branches/release_34/unittests/Makefile.unittest > /usr/lib/llvm-${LLVM_VERSION}/build/unittests/Makefile.unittest && \
    cd /src/klee && \
    make unittests DISABLE_ASSERTIONS=${DISABLE_ASSERTIONS} ENABLE_OPTIMIZED=${ENABLE_OPTIMIZED} ENABLE_SHARED=0 && \
    make install -j `nproc` DISABLE_ASSERTIONS=${DISABLE_ASSERTIONS} ENABLE_OPTIMIZED=${ENABLE_OPTIMIZED} ENABLE_SHARED=0 && \
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
    cd /root

RUN ln -s /usr/lib/clang/3.4/lib/linux/libclang_rt.profile-x86_64.a /usr/lib/libprofile_rt.a
RUN useradd worker
USER worker
ENV LD_LIBRARY_PATH /src/klee/Release+Asserts/lib/:$LD_LIBRARY_PATH