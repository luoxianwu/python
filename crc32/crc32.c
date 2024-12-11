#include <stdint.h>
#include <stdio.h>

// Polynomial for CRC32
#define CRC32_POLYNOMIAL 0x04C11DB7
#define CRC32_INITIAL    0xFFFFFFFF
#define CRC32_FINAL_XOR  0xFFFFFFFF

// Function to compute CRC32
uint32_t crc32(const uint8_t *data, uint16_t length) {
    uint32_t crc = CRC32_INITIAL;
    uint16_t i, j;
    for (i = 0; i < length; i++) {
        crc ^= (uint32_t)data[i] << 24; // Align byte to top of CRC register
        for (j = 0; j < 8; j++) {
            if (crc & 0x80000000) {
                crc = (crc << 1) ^ CRC32_POLYNOMIAL;
            } else {
                crc <<= 1;
            }
        }
    }

    return crc ^ CRC32_FINAL_XOR; // Final XOR step
}



int main(void) {
    const uint8_t data[] = {1, 2, 3, 4, 5}; // Input data array
    uint16_t length = sizeof(data) / sizeof(data[0]); // Length of the data array

    uint32_t crc_result = crc32(data, length); // Calculate CRC32

    printf("CRC32: 0x%08X\n", crc_result); // Print the result

    return 0;
}
