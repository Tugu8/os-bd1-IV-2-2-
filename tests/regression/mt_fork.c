/*
 * mt_fork.c - олон урсгалтай процессын хүүхдийн тест.
 *
 * Үндсэн урсгал нэг pthread үүсгэнэ. Тэр урсгал (үндсэн биш) fork() хийгээд
 * амьд хэвээр хүлээнэ. Кернел хүүхдийг fork хийсэн урсгалын children жагсаалтад
 * бүртгэдэг, харин ps, /proc/<child>/stat-д PPID нь процессын TGID байна.
 * (Урсгал дуусвал хүүхэд нь үндсэн урсгал руу шилждэг тул урсгалыг амьд байлгана.)
 *
 * Гаралт (нэг мөр): "<tgid> <thread_tid> <child_pid>", дараа нь stdin хаагдах
 * хүртэл хүлээнэ (тест скрипт шалгалтаа хийж дуусгаад хаана).
 */
#define _GNU_SOURCE
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

static pid_t child, tid;
static int ready[2];

static void *worker(void *arg)
{
	(void)arg;
	tid = (pid_t)syscall(SYS_gettid);
	child = fork();
	if (child == 0) {
		pause();
		_exit(0);
	}
	if (write(ready[1], "x", 1) != 1)
		return NULL;
	for (;;)
		pause();          /* урсгал амьд үлдэнэ */
	return NULL;
}

int main(void)
{
	pthread_t th;
	char c;

	if (pipe(ready) < 0)
		return 1;
	pthread_create(&th, NULL, worker, NULL);
	if (read(ready[0], &c, 1) != 1)
		return 1;
	printf("%d %d %d\n", getpid(), tid, child);
	fflush(stdout);
	while (read(0, &c, 1) > 0)
		;
	kill(child, SIGTERM);
	waitpid(child, NULL, 0);
	return 0;             /* процесс дуусахад урсгал ч дуусна */
}
