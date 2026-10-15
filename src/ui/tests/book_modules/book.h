/*
 * UI-ийн туршилтын module: зөвхөн номын /proc/pid (/proc/pid_tree-гүй).
 * src/kmod-ийг ОРЛОХГҮЙ — UI-ийн "book" горим ба contract_check.py-г шалгахад.
 *
 *   book_ok.ko    — зөв: kstrtol, task_pid_vnr, simple_read_from_buffer
 *   book_naive.ko — номын skeleton-ий түгээмэл алдаанууд (NAIVE): sscanf ("abc" хүлээн авна),
 *                   tsk->pid (global PID — WSL/контейнерт ps-тэй таарахгүй),
 *                   copy_to_user(rv) count-ийг тоохгүй, static completed туг
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/proc_fs.h>
#include <linux/sched.h>
#include <linux/slab.h>
#include <linux/uaccess.h>
#include <linux/pid.h>

#define BUFFER_SIZE 128
static long l_pid;

static ssize_t proc_read(struct file *file, char __user *usr_buf, size_t count, loff_t *pos)
{
	char buffer[BUFFER_SIZE];
	struct task_struct *tsk;
	int rv = 0;
#ifdef NAIVE
	static int completed;
	if (completed) { completed = 0; return 0; }
#endif
	rcu_read_lock();
	tsk = pid_task(find_vpid(l_pid), PIDTYPE_PID);
	if (tsk)
		rv = scnprintf(buffer, sizeof(buffer), "command = [%s] pid = [%d] state = [%u]\n",
#ifdef NAIVE
		               tsk->comm, tsk->pid, READ_ONCE(tsk->__state));
#else
		               tsk->comm, task_pid_vnr(tsk), READ_ONCE(tsk->__state));
#endif
	rcu_read_unlock();
	if (!tsk)
		return 0;
#ifdef NAIVE
	completed = 1;
	if (copy_to_user(usr_buf, buffer, rv))      /* count-ийг тоохгүй — номын skeleton */
		rv = -1;
	return rv;
#else
	return simple_read_from_buffer(usr_buf, count, pos, buffer, rv);
#endif
}

static ssize_t proc_write(struct file *file, const char __user *usr_buf, size_t count, loff_t *pos)
{
	char *k_mem;
	long val;
	int rv = 0;
	if (count == 0 || count > 32)
		return -EINVAL;
	k_mem = kmalloc(count + 1, GFP_KERNEL);
	if (!k_mem)
		return -ENOMEM;
	if (copy_from_user(k_mem, usr_buf, count)) { kfree(k_mem); return -EFAULT; }
	k_mem[count] = 0;
#ifdef NAIVE
	if (sscanf(k_mem, "%ld", &val) == 1)        /* "12abc" → 12, "abc" → өөрчлөгдөхгүй */
		l_pid = val;
#else
	rv = kstrtol(k_mem, 10, &val);
	if (!rv && val < 0)
		rv = -EINVAL;
	if (!rv)
		l_pid = val;
#endif
	kfree(k_mem);
	return rv ? rv : count;
}

static const struct proc_ops ops = { .proc_read = proc_read, .proc_write = proc_write };
static int __init m_init(void) { return proc_create("pid", 0666, NULL, &ops) ? 0 : -ENOMEM; }
static void __exit m_exit(void) { remove_proc_entry("pid", NULL); }
module_init(m_init);
module_exit(m_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("IV-2-2 UI test fixture: book-only /proc/pid");
