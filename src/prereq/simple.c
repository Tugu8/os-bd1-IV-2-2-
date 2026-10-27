/*
 * simple.c - OSC (2018) 2-р бүлэг, Programming Project "Linux Kernel Modules", I хэсэг
 *
 * Module ачаалах/буулгахад kernel log руу (dmesg) мэдээлэл бичнэ:
 *   - GOLDEN_RATIO_PRIME (шинэ kernel-д GOLDEN_RATIO_32/64, <linux/hash.h>)
 *   - gcd(3300, 24)  (<linux/gcd.h>)
 *   - jiffies ба HZ — ачаалсан/буулгасан хоорондох хугацаа
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/hash.h>
#include <linux/gcd.h>
#include <linux/jiffies.h>

static unsigned long load_jiffies;

static int __init simple_init(void)
{
	load_jiffies = jiffies;
	pr_info("simple: Loading Kernel Module\n");
	pr_info("simple: GOLDEN_RATIO_PRIME = %llu\n", (unsigned long long)GOLDEN_RATIO_64);
	pr_info("simple: jiffies = %lu, HZ = %d\n", load_jiffies, HZ);
	return 0;
}

static void __exit simple_exit(void)
{
	unsigned long now = jiffies;

	pr_info("simple: gcd(3300, 24) = %lu\n", gcd(3300, 24));
	pr_info("simple: jiffies = %lu, %u ms since load\n", now,
		jiffies_to_msecs(now - load_jiffies));
	pr_info("simple: Removing Kernel Module\n");
}

module_init(simple_init);
module_exit(simple_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("OSC Ch.2 simple module (IV-2-2 prereq)");
MODULE_AUTHOR("IV-2-2");
