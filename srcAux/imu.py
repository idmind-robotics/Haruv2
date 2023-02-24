#! /usr/bin/env python

from machine import Pin, SoftI2C
import time

DEVICE_ADDR = 0x4c

SAMPLE_RATE_REGISTER = 0x08
SAMPLE_RATE_50HZ = 0x11
MC34X9_REG_RANGE_C = 0x20
MODE_REGISTER = 0x07
MODE_STANDBY = 0x00

DEVICE_STATUS_REGISTER = 0x07

XOUT_L_REGISTER = 0x0D
XOUT_H_REGISTER = 0x0E
YOUT_L_REGISTER = 0x0F
YOUT_H_REGISTER = 0x10
ZOUT_L_REGISTER = 0x11
ZOUT_H_REGISTER = 0x12

MODE_WAKE = 0x01
MOTION_CONTROL_REGISTER = 0x09
INTERRUPT_ENABLE_REGISTER = 0x06
INTERRUPT_MASK = 0b1000
MC34X9_RANGE_12G   = 0b100
SHAKE_THRESHOLD_REGISTER_LSB = 0x46
SHAKE_THRESHOLD_REGISTER_MSB = 0x47
SHAKE_P2P_DURATION_AND_COUNT_REGISTER_LSB = 0x48
SHAKE_P2P_DURATION_AND_COUNT_REGISTER_MSB = 0x49
SHAKE_THRESHOLD = 300
SHAKE_P2P_DURATION_AND_COUNT = 1 < 4 & 10

class IMU:
    def __init__(self):
        SCL = Pin(22, Pin.OUT)
        SDA = Pin(21, Pin.OUT)
        self.i2c = SoftI2C(SCL, SDA)
        devices = self.i2c.scan()
        self.accel_x = 0
        self.accel_y = 0
        self.accel_z = 0
        # if len(devices) == 0:
        #     print("No i2c device !")
        # else:
        #     print('i2c devices found:',len(devices))
        #     for device in devices:  
        #         print("Decimal address: ",device," | Hexa address: ",hex(device))

    def setup_imu(self):
         # set sample rate to 50Hz
        self.i2c.writeto_mem(DEVICE_ADDR, SAMPLE_RATE_REGISTER, bytearray([SAMPLE_RATE_50HZ]))
        
        value = self.i2c.readfrom(DEVICE_ADDR, MC34X9_REG_RANGE_C, 1)
        value = value[0] & 0b00000111
        value |= (MC34X9_RANGE_12G << 4) & 0x70
        self.i2c.writeto_mem(DEVICE_ADDR, MC34X9_REG_RANGE_C, bytearray([value]))
        # set mode to WAKE
        self.i2c.writeto_mem(DEVICE_ADDR, DEVICE_STATUS_REGISTER, bytearray([MODE_WAKE]))
        # read device status
        device_status = self.i2c.readfrom(DEVICE_ADDR, DEVICE_STATUS_REGISTER, 1)
        is_wake = device_status[0] & 0b00000011
        # print("Device is in %s mode" % ("WAKE" if is_wake else "STANDBY"))
        

        # self.i2c.writeto_mem(DEVICE_ADDR, MOTION_CONTROL_REGISTER, bytearray([ INTERRUPT_MASK ]))
        # self.i2c.writeto_mem(DEVICE_ADDR, INTERRUPT_ENABLE_REGISTER, bytearray([ INTERRUPT_MASK ]))
        # self.i2c.writeto_mem(DEVICE_ADDR, SHAKE_THRESHOLD_REGISTER_LSB, bytearray([ SHAKE_THRESHOLD & 0xff ]))
        # self.i2c.writeto_mem(DEVICE_ADDR, SHAKE_THRESHOLD_REGISTER_MSB, bytearray([ SHAKE_THRESHOLD >> 8 ]))
        # self.i2c.writeto_mem(DEVICE_ADDR, SHAKE_P2P_DURATION_AND_COUNT_REGISTER_LSB, bytearray([ SHAKE_P2P_DURATION_AND_COUNT & 0xff ]))
        # self.i2c.writeto_mem(DEVICE_ADDR, SHAKE_P2P_DURATION_AND_COUNT_REGISTER_MSB, bytearray([ SHAKE_P2P_DURATION_AND_COUNT >> 8 ]))

    def parse_acceleration(self, rawData):
        #{2g, 4g, 8g, 16g, 12g}
        # range = [ 19.614, 39.228, 78.456, 156.912, 117.684 ]
        # 16bit
        range = 78.456 #19.614
        resolution = 32768.0

        # Read the six raw data registers into data array
        x = int(rawData[1] << 8 | rawData[0])
        y = int(rawData[3] << 8 | rawData[2])
        z = int(rawData[5] << 8 | rawData[4])
        
        
        accel_x = (float) (x) / resolution * range
        accel_y = (float) (y) / resolution * range
        accel_z = (float) (z) / resolution * range

        return accel_x , accel_y, accel_z
        # return x,y,z
    
    def combine_register_values(self, h, l):
        if not h[0] & 0x80:
            return h[0] << 8 | l[0]
        return -((h[0] ^ 255) << 8) |  (l[0] ^ 255) + 1
        
    def read(self):
        accel_x_h = self.i2c.readfrom_mem(DEVICE_ADDR, XOUT_H_REGISTER, 1)
        accel_x_l = self.i2c.readfrom_mem(DEVICE_ADDR, XOUT_L_REGISTER, 1)
        accel_y_h = self.i2c.readfrom_mem(DEVICE_ADDR, YOUT_H_REGISTER, 1)
        accel_y_l = self.i2c.readfrom_mem(DEVICE_ADDR, YOUT_L_REGISTER, 1)
        accel_z_h = self.i2c.readfrom_mem(DEVICE_ADDR, ZOUT_H_REGISTER, 1)
        accel_z_l = self.i2c.readfrom_mem(DEVICE_ADDR, ZOUT_L_REGISTER, 1)
        accel = self.i2c.readfrom(DEVICE_ADDR, XOUT_L_REGISTER, 6)
        # print(accel)
        accx = self.combine_register_values(accel_x_h, accel_x_l) / 32768.0
        accy = self.combine_register_values(accel_y_h, accel_y_l) / 32768.0
        accz = self.combine_register_values(accel_z_h, accel_z_l) / 32768.0
        # self.accel_x, self.accel_y, self.accel_z = self.parse_acceleration(accel)
        # print("X: %.3f | Y: %.3f | Z: %.3f" % (
        #     self.accel_x,
        #     self.accel_y,
        #     self.accel_z))
        # print("X: %.3f | Y: %.3f | Z: %.3f" % (
        #     accx,
        #     accy,
        #     self.accel_z))

        return self.combine_register_values(accel_x_h, accel_x_l) / 32768.0, self.combine_register_values(accel_y_h, accel_y_l) / 32768.0, self.combine_register_values(accel_z_h, accel_z_l) / 32768.0

        # return self.accel_x, self.accel_y, self.accel_z
    
    def loop(self):
        while True:
            time.sleep_ms(1000)
            self.read()
            # read acceleration values
            