# UI-ийн туршилтын module-ууд (book.h-ийг үз). Kbuild зайтай замд ажилладаггүй тул
# шаардлагатай бол хуулж хөрвүүлнэ:  cp -r src/ui/tests/book_modules /tmp/bm && make -C /tmp/bm
#   sudo rmmod pid; sudo insmod book_ok.ko      → UI "book" горим, contract_check: 15 ✔ 1 ⚠
#   sudo rmmod book_ok; sudo insmod book_naive.ko → contract_check: 3 ✖ (global PID, copy_to_user, sscanf)
obj-m := book_ok.o book_naive.o
ccflags-y := -I$(src)

WSL_SRC := /usr/src/WSL2-Linux-Kernel
KDIR ?= $(if $(wildcard /lib/modules/$(shell uname -r)/build),/lib/modules/$(shell uname -r)/build,$(WSL_SRC))

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean
