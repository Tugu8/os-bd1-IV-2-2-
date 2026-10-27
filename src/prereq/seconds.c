/*
 * seconds.c - OSC (2018) 2-р бүлэг, Programming Project, Assignment 2: /proc/seconds
 *
 *   $ sudo insmod seconds.ko; sleep 3; cat /proc/seconds
 *   3
 *
 * Module ачаалснаас хойш өнгөрсөн секунд = (jiffies - эхний jiffies) / HZ.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/jiffies.h>

#define PROC_NAME "seconds"

static unsigned long start_jiffies;

static int seconds_show(struct seq_file *m, void *v)
{
	seq_printf(m, "%lu\n", (jiffies - start_jiffies) / HZ);
	return 0;
}

static int seconds_open(struct inode *inode, struct file *file)
{
	return single_open(file, seconds_show, NULL);
}

static const struct proc_ops seconds_ops = {
	.proc_open    = seconds_open,
	.proc_read    = seq_read,
	.proc_lseek   = seq_lseek,
	.proc_release = single_release,
};

static int __init seconds_init(void)
{
	start_jiffies = jiffies;
	if (!proc_create(PROC_NAME, 0444, NULL, &seconds_ops))
		return -ENOMEM;
	pr_info("seconds: /proc/%s created\n", PROC_NAME);
	return 0;
}

static void __exit seconds_exit(void)
{
	remove_proc_entry(PROC_NAME, NULL);
	pr_info("seconds: /proc/%s removed after %lu s\n", PROC_NAME,
		(jiffies - start_jiffies) / HZ);
}

module_init(seconds_init);
module_exit(seconds_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("OSC Ch.2 /proc/seconds (IV-2-2 prereq)");
MODULE_AUTHOR("IV-2-2");
