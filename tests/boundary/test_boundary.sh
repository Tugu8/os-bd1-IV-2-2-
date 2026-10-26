#!/usr/bin/env bash

# Boundary and error tests for the /proc/pid kernel module

PASS=0
FAIL=0  

echo "=== Boundary and error tests for /proc/pid ==="
echo



# Print the results of test
report_result() {
    
    if [ "$1" -eq 0 ]; then
        echo "[PASS] $2"
        PASS=$((PASS + 1))

    else
        echo "[FAIL] $2"
        FAIL=$((FAIL + 1))
    fi
}



# Check if invalid PID is rejected with expected error
test_invalid_input() {
    input="$1"
    expected_error="$2"
    description="$3"

    if error_output=$(printf '%s\n' "$input" | sudo tee /proc/pid 2>&1); then
        echo "Unexpected output:"
        printf '%s\n' "$error_output"
        report_result 1 "$description"

    else
        echo "Actual error:"
        printf '%s\n' "$error_output"

        if printf '%s\n' "$error_output" | grep -Fqi "$expected_error"; then
            report_result 0 "$description"

        else
            report_result 1 "$description"
        fi
    fi
}
# Updated each tests after writing the function above



# Check if the kernel module is loaded
if [ ! -e /proc/pid ]; then
    echo "[ERROR] /proc/pid does not exist."
    echo "Please load the pid kernel module before running the tests."
    exit 1
fi



# Verifying that valid PID can be written before testing invalid inputs
if ! printf '%s\n' "$$" | sudo tee /proc/pid >/dev/null 2>&1; then
    echo "[ERROR] Could not write valid PID to /proc/pid."
    exit 1
fi

echo "[INFO] /proc/pid is ready for boundary testing."
echo



# Test 1: Reject alphabetic inputs
echo "Test 1: Alphabetic input (abc)"

test_invalid_input "abc" "Invalid argument" "Alphabetic input is rejected"

echo



# Test 2: Reject negative PID
echo "Test 2: Negative PID (-5)"

test_invalid_input "-5" "Invalid argument" "Negative PID is rejected"

echo



# Test 3: Reject empty input
echo "Test 3: Empty input"

test_invalid_input "" "Invalid argument" "Empty input is rejected"

echo



# Test 4: Reject zero PID
echo "Test 4: Zero PID (0)"

test_invalid_input "0" "Invalid argument" "Zero PID is rejected"

echo



# Test 5: Reject a very large PID
# echo "Test 5: Very large PID (99999999)"    
# # PID_MAX_LIMIT = 4,194,304 larger than PID limit but fits inside long integer

# if error_output=$(printf '%s\n' "99999999" | sudo tee /proc/pid 2>&1); then
#     echo "Unexpected output:"
#     printf '%s\n' "$error_output"
#     report_result 1 "Very large PID is rejected"

# else
#     echo "Actual error:"
#     printf '%s\n' "$error_output"
#     report_result 0 "Very large PID is rejected"
# fi

# echo
echo "Test 5: Very large PID (99999999)"

test_invalid_input "99999999" "Invalid argument" "Very large PID is rejected"

echo



# Test 6: Reject a number that causes integer overflow
# echo "Test 6: Integer overflow"
# # 30-digit number because module has define MAX_INPUT_LEN 32 input-length restriction

# if error_output=$(printf '%s\n' "999999999999999999999999999999" | sudo tee /proc/pid 2>&1); then
#     echo "Unexpected output:"
#     printf '%s\n' "$error_output"
#     report_result 1 "Integer overflow input is rejected"

# else
#     echo "Actual error:"
#     printf '%s\n' "$error_output"
#     report_result 0 "Integer overflow input is rejected"
# fi

# echo
echo "Test 6: Integer overflow"

test_invalid_input "999999999999999999999999999999" "Numerical result out of range" "Integer overflow input is rejected"

echo



# Test 7: Reject input longer than 32 bytes
echo "Test 7: Input longer than 32 bytes"

long_input="123456789012345678901234567890123"

test_invalid_input "$long_input" "Invalid argument" "Input longer than 32 bytes is rejected"

echo



# Final boundary test results
echo "=== Boundary Test Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"

# Return a failure status if any test failed
if [ "$FAIL" -gt 0 ]; then
    exit 1

else
    exit 0
fi