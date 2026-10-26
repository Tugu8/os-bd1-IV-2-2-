# src/prereq — OSC 2-р бүлгийн бэлтгэл kernel module-ууд
#   make            — simple.ko hello.ko jiffies.ko seconds.ko
#   sudo make test  — module бүрийг ачаалж, /proc-оос уншиж, буулгана (PASS/FAIL)
#   make clean
obj-m := simple.o hello.o jiffies.o seconds.o

KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KDIR) M=$(CURDIR) clean

test: all
	@bash $(CURDIR)/test_prereq.sh
