/*
 * jiffies.c - OSC (2018) 2-р бүлэг, Programming Project, Assignment 1: /proc/jiffies
 *
 *   $ cat /proc/jiffies
 *   4295123456
 *
 * Уншиж буй агшны jiffies-ийн утгыг хэвлэнэ (HZ удаа/секунд нэмэгдэнэ).
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/jiffies.h>

#define PROC_NAME "jiffies"

static int jiffies_show(struct seq_file *m, void *v)
{
	seq_printf(m, "%lu\n", jiffies);
	return 0;
}

static int jiffies_open(struct inode *inode, struct file *file)
{
	return single_open(file, jiffies_show, NULL);
}

static const struct proc_ops jiffies_ops = {
	.proc_open    = jiffies_open,
	.proc_read    = seq_read,
	.proc_lseek   = seq_lseek,
	.proc_release = single_release,
};

static int __init jiffies_init(void)
{
	if (!proc_create(PROC_NAME, 0444, NULL, &jiffies_ops))
		return -ENOMEM;
	pr_info("jiffies: /proc/%s created (HZ = %d)\n", PROC_NAME, HZ);
	return 0;
}

static void __exit jiffies_exit(void)
{
	remove_proc_entry(PROC_NAME, NULL);
	pr_info("jiffies: /proc/%s removed\n", PROC_NAME);
}

module_init(jiffies_init);
module_exit(jiffies_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("OSC Ch.2 /proc/jiffies (IV-2-2 prereq)");
MODULE_AUTHOR("IV-2-2");
