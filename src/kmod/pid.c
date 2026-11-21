/*
 * pid.c - /proc/pid kernel module
 *
 * /proc/pid файл руу PID бичихэд тухайн task-ийн мэдээллийг
 * /proc/pid-ээс уншиж болно.
 *
 * OSC (2018) 3-р бүлэг, Programming Project 2
 *
 * v2 (БД2) өөрчлөлт:
 *  - Хүүхдийг RCU-ээр хамгаалагдсан процессын жагсаалтаас (for_each_process)
 *    real_parent-ийн TGID-ээр олно. Өмнө нь RCU хамгаалдаггүй task->children
 *    жагсаалтыг гүйдэг байсан (түүний tasklist_lock module-д export хийгдээгүй).
 *  - Олон урсгалтай процесс: аль ч урсгалын хүүхэд гарна, ppid нь эцгийн
 *    TGID (ps, /proc/<pid>/stat-тай ижил).
 *  - Нээсэн файл бүр өөрийн PID-тэй: нэг fd-ээр бичээд, lseek(0) хийж
 *    уншвал өөр процесс зэрэг бичсэн ч өөрийн PID-ийн мэдээллийг авна.
 *    echo/cat (тусдаа нээлт) нь өмнөх шигээ сүүлийн глобал PID-ийг уншина.
 */
#include <linux/init.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pid.h>
#include <linux/proc_fs.h>
#include <linux/rcupdate.h>
#include <linux/sched.h>
#include <linux/sched/signal.h>
#include <linux/threads.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

#define PROC_NAME "pid"
#define MAX_INPUT_LEN 32

/* хамгийн сүүлд бичсэн PID (бүх нээлтэд нийтлэг, номын echo/cat горим) */
static long l_pid;

/* нэг нээлтэд хамаарах төлөв: энэ fd-ээр бичсэн PID */
struct pid_ctx {
	long pid;	/* 0 = энэ fd-ээр бичээгүй, глобал l_pid-ийг ашиглана */
};

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
	struct pid_ctx *ctx = m->private;
	struct task_struct *task, *parent, *p;
	long pid = ctx->pid ? ctx->pid : READ_ONCE(l_pid);

	rcu_read_lock();
	task = pid_task(find_vpid(pid), PIDTYPE_PID);
	if (!task)
		goto out;

	seq_printf(m, "command = [%s] pid = [%d] state = [%u]\n",
		   task->comm, task_pid_vnr(task), READ_ONCE(task->__state));

	/* real_parent нь __rcu заагч; эцгийн TGID-ийг хэвлэнэ (ps-тэй ижил) */
	parent = rcu_dereference(task->real_parent);
	if (pid_alive(task) && parent && parent != task)
		seq_printf(m, "parent = [%s] ppid = [%d]\n",
			   parent->group_leader->comm, task_tgid_vnr(parent));

	/*
	 * task->children жагсаалтыг kernel tasklist_lock-оор хамгаалдаг ч тэр
	 * түгжээ module-д export хийгдээгүй. Харин процессын жагсаалт (tasks)
	 * RCU-ээр хамгаалагдсан (list_add_tail_rcu / list_del_rcu) тул бүх
	 * процессыг гүйж, эцгийнх нь TGID таарсныг хүүхэд гэж үзнэ. Ингэхэд аль
	 * ч урсгалын fork хийсэн хүүхэд гарна (олон урсгалтай процесс).
	 */
	if (!pid_alive(task))
		goto out;
	for_each_process(p) {
		struct task_struct *rp = rcu_dereference(p->real_parent);

		if (p != task && rp && rp->tgid == task->tgid)
			seq_printf(m, "child = [%s] pid = [%d] state = [%u]\n",
				   p->comm, task_pid_vnr(p),
				   READ_ONCE(p->__state));
	}
out:
	rcu_read_unlock();
	return 0;
}

static int proc_open(struct inode *inode, struct file *file)
{
	struct pid_ctx *ctx;
	int ret;

	ctx = kzalloc(sizeof(*ctx), GFP_KERNEL);
	if (!ctx)
		return -ENOMEM;

	ret = single_open(file, pid_show, ctx);
	if (ret)
		kfree(ctx);
	return ret;
}

static int proc_release(struct inode *inode, struct file *file)
{
	struct seq_file *m = file->private_data;
	struct pid_ctx *ctx = m->private;

	single_release(inode, file);
	kfree(ctx);
	return 0;
}

static ssize_t proc_write(struct file *file, const char __user *usr_buf,
			  size_t count, loff_t *pos)
{
	struct seq_file *m = file->private_data;
	struct pid_ctx *ctx = m->private;
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

	ctx->pid = val;
	WRITE_ONCE(l_pid, val);
	return count;
}

static const struct proc_ops pid_proc_ops = {
	.proc_open = proc_open,
	.proc_read = seq_read,
	.proc_write = proc_write,
	.proc_lseek = seq_lseek,
	.proc_release = proc_release,
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
MODULE_VERSION("2.0");
