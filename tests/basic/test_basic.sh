#!/usr/bin/env bash

# basic tests for the /proc/pid kernel module

PASS=0
FAIL=0

echo "=== Basic tests for /proc/pid ==="
echo



# print the results of the tests
report_result() {

    if [ "$1" -eq 0 ]; then
        echo "[PASS] $2"
        PASS=$((PASS + 1))

    else
        echo "[FAIL] $2"
        FAIL=$((FAIL + 1))
    fi
}



# check if the kernel module is loaded
if [ ! -e /proc/pid ]; then
    echo "[ERROR] /proc/pid does not exist."
    echo "Please load the pid kernel module before running the tests."
    exit 1

fi

echo "[INFO] /proc/pid exists. Ready to run tests."
echo



# write a pid to /proc/pid
write_pid() {
    
    printf '%s\n' "$1" | sudo tee /proc/pid >/dev/null 2>&1
}



# Test 1: Read information about this Bash process
test_pid=$$

echo "Test 1: Current Bash process (PID $test_pid)"

if write_pid "$test_pid"; then
    output=$(cat /proc/pid 2>&1)

    if printf '%s\n' "$output" | grep -Fq "pid = [$test_pid]"; then
        report_result 0 "Current process information is returned"

    else
        echo "Actual output:"
        printf '%s\n' "$output"
        report_result 1 "Current process information is returned"

    fi
else
    report_result 1 "Writing the current PID succeeds"

fi

echo



# Test 2: Read information about PID 1 
test_pid=1

echo "Test 2: PID 1"

if write_pid "$test_pid"; then
    output=$(cat /proc/pid 2>&1)

    if printf '%s\n' "$output" | grep -Fq "pid = [1]"; then
        report_result 0 "PID 1 information is returned"

    else
        echo "Actual output:"
        printf '%s\n' "$output"
        report_result 1 "PID 1 information is returned"

    fi
else
    report_result 1 "Writing PID 1 succeeds"

fi

echo



# Test 3: Read information about a non-existent PID
missing_pid=999999

echo "Test 3: Non-existent PID ($missing_pid)"

if ps -p "$missing_pid" > /dev/null 2>&1; then
    echo "[SKIP] PID $missing_pid exists on this system"

else
    if write_pid "$missing_pid"; then
        output=$(cat /proc/pid 2>&1)
        read_status=$?

        if [ "$read_status" -eq 0 ] && [ -z "$output" ]; then
            report_result 0 "Non-existent PID returns no information"
        
        else
            echo "Actual output:"
            printf '%s\n' "$output"
            report_result 1 "Non-existent PID returns no information"

        fi
    else
        report_result 1 "Writing a non-existent PID succeeds"

    fi
fi

echo



# Test 4: Check the parent child process relationship
echo "Test 4: Parent-child process relationship"

# starting a temporary child process
sleep 60 &
child_pid=$!
parent_pid=$$

# read information about the parent process
if write_pid "$parent_pid"; then
    output=$(cat /proc/pid 2>&1)

    if printf '%s\n' "$output" | grep -F "child =" | grep -Fq "pid = [$child_pid]"; then
        report_result 0 "Child process is listed under its parent"

    else
        echo "Actual output:"
        printf '%s\n' "$output"
        report_result 1 "Child process is listed under its parent"

    fi
else
    report_result 1 "Writing the parent PID succeeds"

fi

# stop the temporary child process
kill "$child_pid" 2>/dev/null
wait "$child_pid" 2>/dev/null

echo



# Test 5: Read information about kernel thread
echo "Test 5: Kernel thread PID"

# Find kernel thread
thread_pid=$(ps -e -o pid=,args= | awk '$2 ~ /^\[/ && $2 ~ /\]$/ {print $1; exit}')

if [ -z "$thread_pid" ]; then
    echo "[SKIP] No visible kernel thread was found"

else
    echo "Kernel thread PID: $thread_pid"

    if write_pid "$thread_pid"; then
        output=$(cat /proc/pid 2>&1)

        if printf '%s\n' "$output" | grep -Fq "pid = [$thread_pid]"; then
            report_result 0 "Kernel thread information is returned"
            
        else
            echo "Actual output:"
            printf '%s\n' "$output"
            report_result 1 "Kernel thread information is returned"
        fi
    else
        report_result 1 "Writing the kernel thread PID succeeds"
    fi
fi

echo



# Display the final test results
echo "=== Test Summary ==="
echo "Total passed: $PASS"
echo "Total failed: $FAIL"

# Return a failure status if any test failed
if [ $FAIL -gt 0 ]; then
    exit 1
else
    exit 0
fi
