/*
 * pid.c - /proc/pid kernel module
 *
 * /proc/pid файл руу PID бичихэд тухайн task-ийн мэдээллийг
 * /proc/pid-ээс уншиж болно.
 *
 * OSC (2018) 3-р бүлэг, Programming Project 2
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pid.h>
#include <linux/proc_fs.h>
#include <linux/rcupdate.h>
#include <linux/sched.h>
#include <linux/threads.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

#define PROC_NAME "pid"
#define MAX_INPUT_LEN 32

/* хамгийн сүүлд бичсэн PID */
static long l_pid;

/*
 * Гаралт:
 *   command = [bash] pid = [1395] state = [1]
 *   parent = [gnome-terminal-] ppid = [1200]
 *   child = [vim] pid = [1400] state = [1]
 *   ...
 * Байхгүй PID бол юу ч хэвлэхгүй (read 0 буцаана).
 */
static int pid_show(struct seq_file *m, void *v)
{
	struct task_struct *task, *parent, *child;

	rcu_read_lock();
	task = pid_task(find_vpid(l_pid), PIDTYPE_PID);
	if (!task)
		goto out;

	seq_printf(m, "command = [%s] pid = [%d] state = [%u]\n",
		   task->comm, task->pid, READ_ONCE(task->__state));

	parent = rcu_dereference(task->real_parent);
	if (parent && parent != task)
		seq_printf(m, "parent = [%s] ppid = [%d]\n",
			   parent->comm, parent->pid);

	list_for_each_entry_rcu(child, &task->children, sibling)
		seq_printf(m, "child = [%s] pid = [%d] state = [%u]\n",
			   child->comm, child->pid,
			   READ_ONCE(child->__state));
out:
	rcu_read_unlock();
	return 0;
}

static int proc_open(struct inode *inode, struct file *file)
{
	return single_open(file, pid_show, NULL);
}

static ssize_t proc_write(struct file *file, const char __user *usr_buf,
			  size_t count, loff_t *pos)
{
	char *k_mem;
	long val;
	int ret;

	if (count == 0 || count > MAX_INPUT_LEN)
		return -EINVAL;

	k_mem = kmalloc(count + 1, GFP_KERNEL);
	if (!k_mem)
		return -ENOMEM;

	if (copy_from_user(k_mem, usr_buf, count)) {
		kfree(k_mem);
		return -EFAULT;
	}
	k_mem[count] = '\0';

	/* kstrtol нь төгсгөлийн '\n'-ийг зөвшөөрнө (echo-ийн гаралт) */
	ret = kstrtol(k_mem, 10, &val);
	kfree(k_mem);
	if (ret)
		return ret;
	/* PID нь 1..PID_MAX_LIMIT хооронд байх ёстой */
	if (val <= 0 || val > PID_MAX_LIMIT)
		return -EINVAL;

	l_pid = val;
	return count;
}

static const struct proc_ops pid_proc_ops = {
	.proc_open = proc_open,
	.proc_read = seq_read,
	.proc_write = proc_write,
	.proc_lseek = seq_lseek,
	.proc_release = single_release,
};

static int __init pid_init(void)
{
	if (!proc_create(PROC_NAME, 0666, NULL, &pid_proc_ops))
		return -ENOMEM;

	pr_info("/proc/%s created\n", PROC_NAME);
	return 0;
}

static void __exit pid_exit(void)
{
	remove_proc_entry(PROC_NAME, NULL);
	pr_info("/proc/%s removed\n", PROC_NAME);
}

module_init(pid_init);
module_exit(pid_exit);

MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Task information via /proc/pid");
MODULE_AUTHOR("B242270047");
