/*
 * hello.c - OSC (2018) 2-р бүлэг, Programming Project, II хэсэг: /proc/hello
 *
 *   $ cat /proc/hello
 *   Hello World
 *
 * Номын skeleton нь proc_read дотор `completed` туг ашигладаг. Энд seq_file
 * (single_open) ашигласан тул жижиг буфероор уншсан ч мөр бүтнээрээ гарна —
 * src/kmod/pid.c-тэй ижил арга.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>

#define PROC_NAME "hello"

static int hello_show(struct seq_file *m, void *v)
{
	seq_puts(m, "Hello World\n");
	return 0;
}

static int hello_open(struct inode *inode, struct file *file)
{
	return single_open(file, hello_show, NULL);
}

static const struct proc_ops hello_ops = {
	.proc_open    = hello_open,
	.proc_read    = seq_read,
	.proc_lseek   = seq_lseek,
	.proc_release = single_release,
};

static int __init hello_init(void)
{
	if (!proc_create(PROC_NAME, 0444, NULL, &hello_ops))
		return -ENOMEM;
	pr_info("hello: /proc/%s created\n", PROC_NAME);
	return 0;
}

static void __exit hello_exit(void)
{
	remove_proc_entry(PROC_NAME, NULL);
	pr_info("hello: /proc/%s removed\n", PROC_NAME);
}

module_init(hello_init);
module_exit(hello_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("OSC Ch.2 /proc/hello (IV-2-2 prereq)");
MODULE_AUTHOR("IV-2-2");
