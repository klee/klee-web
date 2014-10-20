FROM ubuntu:14.04
RUN apt-get -y update
RUN apt-get -y upgrade

#Install dependencies
RUN apt-get -y install g++ autoconf libyaml-dev libreadline6 libreadline6-dev zlib1g python-minimal git bison flex bc libcap-dev build-essential libboost-all-dev ncurses-dev cmake wget

#LLVM-GCC Binaries
RUN mkdir /src
WORKDIR /src
RUN wget http://llvm.org/releases/2.9/llvm-gcc4.2-2.9-x86_64-linux.tar.bz2
RUN tar -jxvf llvm-gcc4.2-2.9-x86_64-linux.tar.bz2
ENV C_INCLUDE_PATH /usr/include/x86_64-linux-gnu
ENV CPLUS_INCLUDE_PATH /usr/include/x86_64-linux-gnu
ENV PATH $PATH:/src/llvm-gcc4.2-2.9-x86_64-linux/bin

#LLVM
RUN wget http://llvm.org/releases/2.9/llvm-2.9.tgz
RUN tar -zxvf llvm-2.9.tgz
WORKDIR /src/llvm-2.9
RUN wget https://gist.githubusercontent.com/ilovepjs/55a8d84000cc5d23a48c/raw/a992a62eaab5600994c66a6d42b6eeec80149cdd/llvm_patch
RUN patch -p1 < llvm_patch
RUN ./configure --enable-optimized --enable-assertions
RUN make -j `nproc`

# Build STP
WORKDIR /src
RUN git clone https://github.com/stp/stp.git
WORKDIR /src/stp
RUN mkdir build
WORKDIR build
RUN cmake -G 'Unix Makefiles' /src/stp
RUN make
RUN sudo make install
RUN sudo ldconfig
RUN ulimit -s unlimited

# Build KLEE-uclibc
WORKDIR /src/
RUN git clone --depth 1 --branch klee_0_9_29 https://github.com/klee/klee-uclibc.git
WORKDIR /src/klee-uclibc/
RUN ./configure --with-llvm-config /src/llvm-2.9/Release+Asserts/bin/llvm-config --make-llvm-lib
RUN make -j`nproc`

#Download KLEE
WORKDIR /src/
RUN git clone https://github.com/klee/klee.git
WORKDIR /src/klee
RUN ./configure --enable-posix-runtime --with-stp=/usr/local --with-llvm=/src/llvm-2.9/ --with-uclibc=/src/klee-uclibc/
RUN make ENABLE_OPTIMIZED=1
RUN make check
RUN make test
RUN make unittests
RUN sudo make install

#Remove unnecessary files
RUN rm /src/*.tgz && rm /src/*.tar.bz2
RUN rm -rf /src/klee-uclibc
RUN rm -rf /src/stp
RUN rm -rf /src/llvm-2.9
RUN rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/lib32
RUN rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/man
RUN rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/share
RUN rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/info
RUN rm -rf /src/llvm-gcc4.2-2.9-x86_64-linux/include
RUN rm -rf /src/klee/examples
RUN rm -rf /src/klee/autoconf
RUN rm -rf /src/klee/docs
RUN rm -rf /src/klee/lib
RUN rm -rf /src/klee/runtime
RUN rm -rf /src/klee/scripts
RUN rm -rf /src/klee/test
RUN rm -rf /src/klee/tools
RUN rm -rf /src/klee/unittests
RUN rm -rf /src/klee/utils

#Return to homedir
WORKDIR /root
