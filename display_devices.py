import os
import json
from beautifultable import BeautifulTable
import argparse


unit_id_dict = {
                # Acceleration
                166: 'metersPerSecondPerSecond',
                0: 'squareMeters',
                116: 'squareCentimeters',
                1: 'squareFeet',
                115: 'squareInches',
                # Currency
                105: 'currency1',
                106: 'currency2',
                107: 'currency3',
                108: 'currency4',
                109: 'currency5',
                110: 'currency6',
                111: 'currency7',
                112: 'currency8',
                113: 'currency9',
                114: 'currency10',
                # Electrical
                2: 'milliamperes',
                3: 'amperes',
                167: 'amperesPerMeter',
                168: 'amperesPerSquareMeter',
                169: 'ampereSquareMeters',
                199: 'decibels',
                200: 'decibelsMillivolt',
                201: 'decibelsVolt',
                170: 'farads',
                171: 'henrys',
                4: 'ohms',
                172: 'ohmMeters',
                237: 'ohmMeterPerSquareMeter',
                145: 'milliohms',
                122: 'kilohms',
                123: 'megohms',
                190: 'microSiemens',
                202: 'millisiemens',
                173: 'siemens',
                174: 'siemensPerMeter',
                175: 'teslas',
                5: 'volts',
                124: 'millivolts',
                6: 'kilovolts',
                7: 'megavolts',
                8: 'voltAmperes',
                9: 'kilovoltAmperes',
                10: 'megavoltAmperes',
                238: 'ampereSeconds',
                246: 'ampereSquareHours',
                239: 'voltAmpereHours',  # VAh
                240: 'kilovoltAmpereHours',  # kVAh
                241: 'megavoltAmpereHours',  # MVAh
                11: 'voltAmperesReactive',
                12: 'kilovoltAmperesReactive',
                13: 'megavoltAmperesReactive',
                242: 'voltAmpereHoursReactive',  # varh
                243: 'kilovoltAmpereHoursReactive',  # kvarh
                244: 'megavoltAmpereHoursReactive',  # Mvarh
                176: 'voltsPerDegreeKelvin',
                177: 'voltsPerMeter',
                245: 'voltsSquareHours',
                14: 'degreesPhase',
                15: 'powerFactor',
                178: 'webers',
                # Energy
                16: 'joules',
                17: 'kilojoules',
                125: 'kilojoulesPerKilogram',
                126: 'megajoules',
                247: 'joulesPerHours',
                18: 'wattHours',
                19: 'kilowattHours',
                146: 'megawattHours',
                203: 'wattHoursReactive',
                204: 'kilowattHoursReactive',
                205: 'megawattHoursReactive',
                20: 'btus',
                147: 'kiloBtus',
                148: 'megaBtus',
                21: 'therms',
                22: 'tonHours',
                # Enthalpy
                23: 'joulesPerKilogramDryAir',
                149: 'kilojoulesPerKilogramDryAir',
                150: 'megajoulesPerKilogramDryAir',
                24: 'btusPerPoundDryAir',
                117: 'btusPerPound',
                127: 'joulesPerDegreeKelvin',
                # Entropy
                151: 'kilojoulesPerDegreeKelvin',
                152: 'megajoulesPerDegreeKelvin',
                128: 'joulesPerKilogramDegreeKelvin',
                # Force
                153: 'newton',
                # Frequency
                25: 'cyclesPerHour',
                26: 'cyclesPerMinute',
                27: 'hertz',
                129: 'kilohertz',
                130: 'megahertz',
                131: 'perHour',
                28: 'gramsOfWaterPerKilogramDryAir',
                29: 'percentRelativeHumidity',
                194: 'micrometers',
                30: 'millimeters',
                118: 'centimeters',
                193: 'kilometers',
                31: 'meters',
                32: 'inches',
                33: 'feet',
                179: 'candelas',
                180: 'candelasPerSquareMeter',
                34: 'wattsPerSquareFoot',
                35: 'wattsPerSquareMeter',
                36: 'lumens',
                37: 'luxes',
                38: 'footCandles',
                196: 'milligrams',
                195: 'grams',
                39: 'kilograms',
                40: 'poundsMass',
                41: 'tons',
                154: 'gramsPerSecond',
                155: 'gramsPerMinute',
                42: 'kilogramsPerSecond',
                43: 'kilogramsPerMinute',
                44: 'kilogramsPerHour',
                119: 'poundsMassPerSecond',
                45: 'poundsMassPerMinute',
                46: 'poundsMassPerHour',
                156: 'tonsPerHour',
                132: 'milliwatts',
                47: 'watts',
                48: 'kilowatts',
                49: 'megawatts',
                50: 'btusPerHour',
                157: 'kiloBtusPerHour',
                51: 'horsepower',
                52: 'tonsRefrigeration',
                53: 'pascals',
                133: 'hectopascals',
                54: 'kilopascals',
                253: 'pascalSeconds',
                134: 'millibars',
                55: 'bars',
                56: 'poundsForcePerSquareInch',
                206: 'millimetersOfWater',
                57: 'centimetersOfWater',
                58: 'inchesOfWater',
                59: 'millimetersOfMercury',
                60: 'centimetersOfMercury',
                61: 'inchesOfMercury',
                62: 'degreesCelsius',
                63: 'degreesKelvin',
                181: 'degreesKelvinPerHour',
                182: 'degreesKelvinPerMinute',
                64: 'degreesFahrenheit',
                65: 'degreeDaysCelsius',
                66: 'degreeDaysFahrenheit',
                120: 'deltaDegreesFahrenheit',
                121: 'deltaDegreesKelvin',
                67: 'years',
                68: 'months',
                69: 'weeks',
                70: 'days',
                71: 'hours',
                72: 'minutes',
                73: 'seconds',
                158: 'hundredthsSeconds',
                159: 'milliseconds',
                160: 'newtonMeters',
                161: 'millimetersPerSecond',
                162: 'millimetersPerMinute',
                74: 'metersPerSecond',
                163: 'metersPerMinute',
                164: 'metersPerHour',
                75: 'kilometersPerHour',
                76: 'feetPerSecond',
                77: 'feetPerMinute',
                78: 'milesPerHour',
                79: 'cubicFeet',
                248: 'cubicFeetPerDay',
                80: 'cubicMeters',
                249: 'cubicMetersPerDay',
                81: 'imperialGallons',
                197: 'milliliters',
                82: 'liters',
                83: 'usGallons',
                142: 'cubicFeetPerSecond',
                84: 'cubicFeetPerMinute',
                191: 'cubicFeetPerHour',
                85: 'cubicMetersPerSecond',
                165: 'cubicMetersPerMinute',
                135: 'cubicMetersPerHour',
                86: 'imperialGallonsPerMinute',
                198: 'millilitersPerSecond',
                87: 'litersPerSecond',
                88: 'litersPerMinute',
                136: 'litersPerHour',
                89: 'usGallonsPerMinute',
                192: 'usGallonsPerHour',
                90: 'degreesAngular',
                91: 'degreesCelsiusPerHour',
                92: 'degreesCelsiusPerMinute',
                93: 'degreesFahrenheitPerHour',
                94: 'degreesFahrenheitPerMinute',
                183: 'jouleSeconds',
                186: 'kilogramsPerCubicMeter',
                137: 'kilowattHoursPerSquareMeter',
                138: 'kilowattHoursPerSquareFoot',
                139: 'megajoulesPerSquareMeter',
                140: 'megajoulesPerSquareFoot',
                95: 'noUnits',
                187: 'newtonSeconds',
                188: 'newtonsPerMeter',
                96: 'partsPerMillion',
                97: 'partsPerBillion',
                98: 'percent',
                143: 'percentObscurationPerFoot',
                144: 'percentObscurationPerMeter',
                99: 'percentPerSecond',
                100: 'perMinute',
                101: 'perSecond',
                102: 'psiPerDegreeFahrenheit',
                103: 'radians',
                184: 'radiansPerSecond',
                104: 'revolutionsPerMinute',
                185: 'squareMetersPerNewton',
                189: 'wattsPerMeterPerDegreeKelvin',
                141: 'wattsPerSquareMeterDegreeKelvin',
                207: 'perMille',
                208: 'gramsPerGram',
                209: 'kilogramsPerKilogram',
                210: 'gramsPerKilogram',
                211: 'milligramsPerGram',
                212: 'milligramsPerKilogram',
                213: 'gramsPerMilliliter',
                214: 'gramsPerLiter',
                215: 'milligramsPerLiter',
                216: 'microgramsPerLiter',
                217: 'gramsPerCubicMeter',
                218: 'milligramsPerCubicMeter',
                219: 'microgramsPerCubicMeter',
                220: 'nanogramsPerCubicMeter',
                221: 'gramsPerCubicCentimeter',
                250: 'wattHoursPerCubicMeter',
                251: 'joulesPerCubicMeter',
                222: 'becquerels',
                223: 'kilobecquerels',
                224: 'megabecquerels',
                225: 'gray',
                226: 'milligray',
                227: 'microgray',
                228: 'sieverts',
                229: 'millisieverts',
                230: 'microsieverts',
                231: 'microsievertsPerHour',
                232: 'decibelsA',
                233: 'nephelometricTurbidityUnit',
                234: 'pH',
                235: 'gramsPerSquareMeter',
                236: 'minutesPerDegreeKelvin'
}


def display_devices(file_prefix=None):
    table1 = BeautifulTable()
    table2 = BeautifulTable()
    table3 = BeautifulTable()
    table4 = BeautifulTable()
    hold_ovrvw_table1 = BeautifulTable()
    hold_table1 = BeautifulTable()
    inpt_ovrvw_table1 = BeautifulTable()
    inpt_table1 = BeautifulTable()

    table1.column_headers = ['BACnet Id', 'Name', 'IP', 'Modbus Id']
    table2.column_headers = ['BACnet Id', 'Description']
    table3.column_headers = ['BACnet Id', 'Map Name', 'Map Rev', 'Meter Name']
    table4.column_headers = ['BACnet Id', 'Modbus TO', 'COV Subscribe']
    hold_ovrvw_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons', 'Group gap']
    hold_table1.column_headers = ['Object Instance', 'Object Name', 'Reg', 'Format', 'Poll', 'Units']
    inpt_ovrvw_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons', 'Group gap']
    inpt_table1.column_headers = ['Object Instance', 'Object Name', 'Reg', 'Format', 'Poll', 'Units']

    dev_list = []
    hold_reg_ovrvw_list = []
    hold_reg_list = []
    inpt_reg_ovrvw_list = []
    inpt_reg_list = []

    for dev_filename in os.listdir(os.getcwd() + '/DeviceList'):
        if dev_filename.endswith('.json'):  # and fn.startswith('DRL'):
            json_raw_str = open(os.getcwd() + '/DeviceList/' + dev_filename, 'r')
            map_dict = json.load(json_raw_str)

            device_instance = map_dict.get('deviceInstance')

            if file_prefix is None or file_prefix == str(device_instance):
                device_name = map_dict.get('deviceName', 'SHOULD HAVE NAME')
                device_ip = map_dict.get('deviceIP', 'MUST HAVE IP')
                modbus_id = map_dict.get('modbusId', 'MUST HAVE ID')
                device_description = map_dict.get('deviceDescription', 'should have description')
                map_name = map_dict.get('mapName', 'MAP NAME')
                map_rev = map_dict.get('mapRev', 'MAP REV')
                meter_model_name = map_dict.get('meterModelName', 'MODEL NAME')
                modbus_port = map_dict.get('modbusPort', 'MUST HAVE MODBUS PORT')
                cov_subscribe = map_dict.get('covSubscribe', '-')

                dev_list.append([device_instance, device_name, device_ip, modbus_id, device_description, map_name,
                                 map_rev, meter_model_name, modbus_port, cov_subscribe])

                if 'holdingRegisters' in map_dict:
                    hold_map_dict = map_dict['holdingRegisters']
                    registers_list = hold_map_dict['registers']
                    num_regs = len(registers_list)
                    word_order = hold_map_dict.get('wordOrder', 'MUST HAVE THIS')
                    polling_time = hold_map_dict.get('pollingTime', 'MUST HAVE THIS')
                    request_timeout = hold_map_dict.get('requestTimeout', 'MUST HAVE THIS')
                    group_consecutive = hold_map_dict.get('groupConsecutive', 'MUST HAVE THIS')
                    group_gaps = hold_map_dict.get('groupGaps', 'MUST HAVE THIS')

                    hold_reg_ovrvw_list.append([device_instance, num_regs, word_order, polling_time, request_timeout,
                                                group_consecutive, group_gaps])

                    if file_prefix is not None:
                        for reg in registers_list:
                            object_name = reg.get('objectName', 'MUST HAVE THIS')
                            # object_desc = reg.get('objectDescription', '-')
                            object_instance = reg.get('objectInstance', 'MUST HAVE THIS')
                            reg_start = reg.get('start', 'MUST HAVE THIS')
                            reg_format = reg.get('format', 'MUST HAVE THIS')
                            obj_poll = reg.get('poll', '')
                            units_id = unit_id_dict[int(reg.get('unitsId', '95'))]
                            # cov_increment = reg.get('covIncrement', 'default')
                            # point_scale = reg.get('pointScale', '[0,1,0,1]')

                            hold_reg_list.append([object_instance, object_name, reg_start, reg_format, obj_poll,
                                                  units_id])

                else:
                    hold_reg_ovrvw_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

                if 'inputRegisters' in map_dict:
                    inpt_map_dict = map_dict['holdingRegisters']
                    registers_list = inpt_map_dict['registers']
                    num_regs = len(inpt_map_dict['registers'])
                    word_order = inpt_map_dict.get('wordOrder', 'MUST HAVE THIS')
                    polling_time = inpt_map_dict.get('pollingTime', 'MUST HAVE THIS')
                    request_timeout = inpt_map_dict.get('requestTimeout', 'MUST HAVE THIS')
                    group_consecutive = inpt_map_dict.get('groupConsecutive', 'MUST HAVE THIS')
                    group_gaps = inpt_map_dict.get('groupGaps', 'MUST HAVE THIS')

                    inpt_reg_ovrvw_list.append([device_instance, num_regs, word_order, polling_time, request_timeout,
                                                group_consecutive, group_gaps])

                    if file_prefix is not None:
                        for reg in registers_list:
                            object_name = reg.get('objectName', 'MUST HAVE THIS')
                            # object_desc = reg.get('objectDescription', '-')
                            object_instance = reg.get('objectInstance', 'MUST HAVE THIS')
                            reg_start = reg.get('start', 'MUST HAVE THIS')
                            reg_format = reg.get('format', 'MUST HAVE THIS')
                            obj_poll = reg.get('poll', '')
                            units_id = unit_id_dict[int(reg.get('unitsId', '95'))]
                            # cov_increment = reg.get('covIncrement', 'default')
                            # point_scale = reg.get('pointScale', '[0,1,0,1]')

                            inpt_reg_list.append([object_instance, object_name, reg_start, reg_format, obj_poll,
                                                  units_id])
                else:
                    inpt_reg_ovrvw_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

            json_raw_str.close()

    dev_list.sort()
    hold_reg_ovrvw_list.sort()
    hold_reg_list.sort()
    inpt_reg_ovrvw_list.sort()
    inpt_reg_list.sort()

    if len(dev_list) == 0:
        print('Nothing was found!')
    else:
        for ii in range(len(dev_list)):
            table1.append_row([dev_list[ii][0], dev_list[ii][1], dev_list[ii][2], dev_list[ii][3]])
            table2.append_row([dev_list[ii][0], dev_list[ii][4]])
            table3.append_row([dev_list[ii][0], dev_list[ii][5], dev_list[ii][6], dev_list[ii][7]])
            table4.append_row([dev_list[ii][0], dev_list[ii][8], dev_list[ii][9]])

            hold_ovrvw_table1.append_row(hold_reg_ovrvw_list[ii])
            inpt_ovrvw_table1.append_row(inpt_reg_ovrvw_list[ii])

        print(table1, '\n')
        print(table2, '\n')
        print(table3, '\n')
        print(table4, '\n')
        print('HOLDING REGISTERS OVERVIEW')
        print(hold_ovrvw_table1, '\n')
        print('INPUT REGISTERS OVERVIEW')
        print(inpt_ovrvw_table1, '\n')

        if file_prefix is not None:
            if len(hold_reg_list) > 0:
                for ii in range(len(hold_reg_list)):
                    hold_table1.append_row(hold_reg_list[ii])

                print('HOLDING REGISTERS')
                print(hold_table1, '\n')

            if len(inpt_reg_list) > 0:
                for ii in range(len(inpt_reg_list)):
                    inpt_table1.append_row(inpt_reg_list[ii])

                print('INPUT REGISTERS')
                print(inpt_table1, '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Displays info stored in meter jsons in /DeviceList directory.')

    parser.add_argument('-id', '--meter_id', type=str, default=None, help='Shows more in depth info for meter, given 2 '
                                                                          'digit id of meter')
    args = parser.parse_args()

    display_devices(file_prefix=args.meter_id)
