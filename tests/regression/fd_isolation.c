/*
 * fd_isolation.c - /proc/pid-ийг олон процесс зэрэг ашиглах үеийн тест.
 *
 *   ./fd_isolation [workers] [iterations]
 *
 * Ажилчин (worker) бүр өөрийн PID-ийг /proc/pid руу бичиж, хариуд нь өөрийн
 * мэдээлэл ирж байгаа эсэхийг шалгана. Хоёр аргаар:
 *   legacy : open+write+close, дараа нь тусдаа open+read (echo/cat-тай ижил)
 *   samefd : нэг fd-ээр write, lseek(0), read (v2 module-ийн шинэ боломж)
 * Хариуны "pid = [N]" нь өөрийн PID биш бол "mismatch" гэж тоолно.
 */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>

#define PROC "/proc/pid"

static int got_pid(const char *buf)
{
	const char *p = strstr(buf, "pid = [");
	return p ? atoi(p + 7) : -1;
}

static int query_legacy(int pid, char *buf, size_t len)
{
	char in[32];
	int fd, n = snprintf(in, sizeof(in), "%d\n", pid);

	fd = open(PROC, O_WRONLY);
	if (fd < 0 || write(fd, in, n) != n)
		return -1;
	close(fd);
	fd = open(PROC, O_RDONLY);
	if (fd < 0)
		return -1;
	n = read(fd, buf, len - 1);
	close(fd);
	buf[n > 0 ? n : 0] = '\0';
	return 0;
}

static int query_samefd(int pid, char *buf, size_t len)
{
	char in[32];
	int fd, n = snprintf(in, sizeof(in), "%d\n", pid);

	fd = open(PROC, O_RDWR);
	if (fd < 0 || write(fd, in, n) != n)
		return -1;
	lseek(fd, 0, SEEK_SET);
	n = read(fd, buf, len - 1);
	close(fd);
	buf[n > 0 ? n : 0] = '\0';
	return 0;
}

static long run(int workers, int iters, int samefd)
{
	long *bad = mmap(NULL, sizeof(long) * workers, PROT_READ | PROT_WRITE,
			 MAP_SHARED | MAP_ANONYMOUS, -1, 0);
	long total = 0;

	for (int w = 0; w < workers; w++) {
		if (fork() == 0) {
			char buf[4096];
			int me = getpid();

			bad[w] = 0;
			for (int i = 0; i < iters; i++) {
				int r = samefd ? query_samefd(me, buf, sizeof(buf))
					       : query_legacy(me, buf, sizeof(buf));
				if (r < 0 || got_pid(buf) != me)
					bad[w]++;
			}
			_exit(0);
		}
	}
	while (wait(NULL) > 0)
		;
	for (int w = 0; w < workers; w++)
		total += bad[w];
	munmap(bad, sizeof(long) * workers);
	return total;
}

int main(int argc, char **argv)
{
	int workers = argc > 1 ? atoi(argv[1]) : 4;
	int iters = argc > 2 ? atoi(argv[2]) : 5000;
	long legacy = run(workers, iters, 0);
	long samefd = run(workers, iters, 1);
	long n = (long)workers * iters;

	printf("workers=%d iterations=%d (нийт %ld асуулга нэг аргад)\n", workers, iters, n);
	printf("legacy (echo/cat шиг тусдаа open): mismatch %ld / %ld\n", legacy, n);
	printf("samefd (нэг fd, lseek 0)         : mismatch %ld / %ld\n", samefd, n);
	return samefd == 0 ? 0 : 1;
}
