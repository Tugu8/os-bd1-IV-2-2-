CFLAGS ?= -O2 -Wall -Wextra

all: fd_isolation mt_fork

fd_isolation: fd_isolation.c
	$(CC) $(CFLAGS) -o $@ $<

mt_fork: mt_fork.c
	$(CC) $(CFLAGS) -pthread -o $@ $<

clean:
	rm -f fd_isolation mt_fork

.PHONY: all clean
