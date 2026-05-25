# Build all c-vuln-samples binaries with ASan + UBSan enabled.
# These binaries INTENTIONALLY crash to demonstrate the bug; only build them
# inside the Mythos sandbox.

CC ?= clang
CFLAGS = -g -O0 -fsanitize=address,undefined -fno-omit-frame-pointer
LDFLAGS = -fsanitize=address,undefined

SRC = $(wildcard src/*.c)
BIN = $(SRC:src/%.c=bin/%)

all: $(BIN)

bin/%: src/%.c | bin
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

bin:
	mkdir -p bin

clean:
	rm -rf bin

.PHONY: all clean
