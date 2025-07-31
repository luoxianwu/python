#include <stdio.h>
#include <stdint.h>

int main() {
    int16_t wide_value = 300;  // Example value outside int8_t range
    int8_t narrow_value;

    narrow_value = (int8_t)wide_value;

    printf("Original int16_t: %d\n", wide_value);
    printf("Converted int8_t: %d\n", narrow_value); // Output will likely be -44 (300 % 256)
                                                     // due to truncation and interpretation as signed.

    int16_t in_range_value = 100;
    int8_t narrow_value_in_range = (int8_t)in_range_value;
    printf("Original int16_t (in range): %d\n", in_range_value);
    printf("Converted int8_t (in range): %d\n", narrow_value_in_range); // Output: 100

    return 0;
}