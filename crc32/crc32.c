#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <zlib.h>  // Make sure to link zlib when compiling

// Precomputed CRC32 lookup table
uint32_t crc32_table[256];

// Function to generate the CRC32 lookup table
void generate_crc32_table() {
    uint32_t polynomial = 0xEDB88320; // Reversed polynomial used in IEEE 802.3
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t crc = i;
        for (int j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ polynomial;
            } else {
                crc >>= 1;
            }
        }
        crc32_table[i] = crc;
    }
}

// Function to calculate CRC32
uint32_t calculate_crc32(const unsigned char *data, size_t length) {
    uint32_t crc = 0xFFFFFFFF; // Initial value
    for (size_t i = 0; i < length; i++) {
        uint8_t byte = data[i];
        crc = (crc >> 8) ^ crc32_table[(crc ^ byte) & 0xFF];
    }
    return ~crc; // Final XOR
}

uint32_t calculate_crc32_bitwise(const unsigned char *data, size_t length) {
    uint32_t crc = 0xFFFFFFFF; // Initial value
    uint32_t polynomial = 0xEDB88320; // Reversed polynomial used in IEEE 802.3

    for (size_t i = 0; i < length; i++) {
        uint8_t byte = data[i];
        crc ^= byte;
        for (int j = 0; j < 8; j++) { // Process each bit
            if (crc & 1) {
                crc = (crc >> 1) ^ polynomial;
            } else {
                crc >>= 1;
            }
        }
    }
    return ~crc; // Final XOR
}

int main() {
    // Generate the CRC32 lookup table
    generate_crc32_table();

    // Data to calculate CRC32 for
    unsigned char data[] = {1, 2, 3, 4, 5};

    uint32_t crc32_result = crc32(0L, Z_NULL, 0); // Initialize CRC

    crc32_result = crc32(crc32_result, (const unsigned char *)data, strlen(data));

    printf("zlib CRC32: \t%08X\n", crc32_result);

    // Calculate CRC32
    crc32_result = calculate_crc32(data, sizeof(data));

    // Print the CRC32 result in hexadecimal format
    printf("table CRC32: \t%08X\n", crc32_result);


    crc32_result = calculate_crc32_bitwise(data, sizeof(data));

    // Print the CRC32 result in hexadecimal format
    printf("bitwisee CRC32: %08X\n", crc32_result);
    return 0;
}


/*
PS C:\Users\xianw\python\python> gcc crc32.c -lz
PS C:\Users\xianw\python\python> .\a.exe
zlib CRC32:     470B99F4
table CRC32:    470B99F4
bitwisee CRC32: 470B99F4
PS C:\Users\xianw\python\python>
*/