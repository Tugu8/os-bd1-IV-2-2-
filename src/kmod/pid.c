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
#include <linux/slab.h>
#include <linux/uaccess.h>

#define PROC_NAME "pid"
#define MAX_INPUT_LEN 32
#define BUFFER_SIZE 128

/* хамгийн сүүлд бичсэн PID */
static long l_pid;

static ssize_t proc_read(struct file *file, char __user *usr_buf,
			 size_t count, loff_t *pos)
{
	struct task_struct *task;
	char *buf;
	int len = 0;
	ssize_t ret;

	buf = kmalloc(BUFFER_SIZE, GFP_KERNEL);
	if (!buf)
		return -ENOMEM;

	rcu_read_lock();
	task = pid_task(find_vpid(l_pid), PIDTYPE_PID);
	if (task)
		len = scnprintf(buf, BUFFER_SIZE,
				"command = [%s] pid = [%d] state = [%u]\n",
				task->comm, task->pid,
				READ_ONCE(task->__state));
	rcu_read_unlock();

	/* байхгүй PID бол len = 0 тул 0 буцаана */
	ret = simple_read_from_buffer(usr_buf, count, pos, buf, len);
	kfree(buf);
	return ret;
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
	if (val <= 0)
		return -EINVAL;

	l_pid = val;
	return count;
}

static const struct proc_ops pid_proc_ops = {
	.proc_read = proc_read,
	.proc_write = proc_write,
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
