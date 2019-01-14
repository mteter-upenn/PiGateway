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
                 'kilojoulesPerDegreeKelvin':151,
                 'megajoulesPerDegreeKelvin':152,
                 'joulesPerKilogramDegreeKelvin':128,
                # Force
                 'newton':153,
                # Frequency
                 'cyclesPerHour':25,
                 'cyclesPerMinute':26,
                 'hertz':27,
                 'kilohertz':129,
                 'megahertz':130,
                 'perHour':131,
                 'gramsOfWaterPerKilogramDryAir':28,
                 'percentRelativeHumidity':29,
                 'micrometers':194,
                 'millimeters':30,
                 'centimeters':118,
                 'kilometers':193,
                 'meters':31,
                 'inches':32,
                 'feet':33,
                 'candelas':179,
                 'candelasPerSquareMeter':180,
                 'wattsPerSquareFoot':34,
                 'wattsPerSquareMeter':35,
                 'lumens':36,
                 'luxes':37,
                 'footCandles':38,
                 'milligrams':196,
                 'grams':195,
                 'kilograms':39,
                 'poundsMass':40,
                 'tons':41,
                 'gramsPerSecond':154,
                 'gramsPerMinute':155,
                 'kilogramsPerSecond':42,
                 'kilogramsPerMinute':43,
                 'kilogramsPerHour':44,
                 'poundsMassPerSecond':119,
                 'poundsMassPerMinute':45,
                 'poundsMassPerHour':46,
                 'tonsPerHour':156,
                 'milliwatts':132,
                 'watts':47,
                 'kilowatts':48,
                 'megawatts':49,
                 'btusPerHour':50,
                 'kiloBtusPerHour':157,
                 'horsepower':51,
                 'tonsRefrigeration':52,
                 'pascals':53,
                 'hectopascals':133,
                 'kilopascals':54,
                 'pascalSeconds':253,
                 'millibars':134,
                 'bars':55,
                 'poundsForcePerSquareInch':56,
                 'millimetersOfWater':206,
                 'centimetersOfWater':57,
                 'inchesOfWater':58,
                 'millimetersOfMercury':59,
                 'centimetersOfMercury':60,
                 'inchesOfMercury':61,
                 'degreesCelsius':62,
                 'degreesKelvin':63,
                 'degreesKelvinPerHour':181,
                 'degreesKelvinPerMinute':182,
                 'degreesFahrenheit':64,
                 'degreeDaysCelsius':65,
                 'degreeDaysFahrenheit':66,
                 'deltaDegreesFahrenheit':120,
                 'deltaDegreesKelvin':121,
                 'years':67,
                 'months':68,
                 'weeks':69,
                 'days':70,
                 'hours':71,
                 'minutes':72,
                 'seconds':73,
                 'hundredthsSeconds':158,
                 'milliseconds':159,
                 'newtonMeters':160,
                 'millimetersPerSecond':161,
                 'millimetersPerMinute':162,
                 'metersPerSecond':74,
                 'metersPerMinute':163,
                 'metersPerHour':164,
                 'kilometersPerHour':75,
                 'feetPerSecond':76,
                 'feetPerMinute':77,
                 'milesPerHour':78,
                 'cubicFeet':79,
                 'cubicFeetPerDay':248,
                 'cubicMeters':80,
                 'cubicMetersPerDay':249,
                 'imperialGallons':81,
                 'milliliters':197,
                 'liters':82,
                 'usGallons':83,
                 'cubicFeetPerSecond':142,
                 'cubicFeetPerMinute':84,
                 'cubicFeetPerHour':191,
                 'cubicMetersPerSecond':85,
                 'cubicMetersPerMinute':165,
                 'cubicMetersPerHour':135,
                 'imperialGallonsPerMinute':86,
                 'millilitersPerSecond':198,
                 'litersPerSecond':87,
                 'litersPerMinute':88,
                 'litersPerHour':136,
                 'usGallonsPerMinute':89,
                 'usGallonsPerHour':192,
                 'degreesAngular':90,
                 'degreesCelsiusPerHour':91,
                 'degreesCelsiusPerMinute':92,
                 'degreesFahrenheitPerHour':93,
                 'degreesFahrenheitPerMinute':94,
                 'jouleSeconds':183,
                 'kilogramsPerCubicMeter':186,
                 'kilowattHoursPerSquareMeter':137,
                 'kilowattHoursPerSquareFoot':138,
                 'megajoulesPerSquareMeter':139,
                 'megajoulesPerSquareFoot':140,
                 'noUnits':95,
                 'newtonSeconds':187,
                 'newtonsPerMeter':188,
                 'partsPerMillion':96,
                 'partsPerBillion':97,
                 'percent':98,
                 'percentObscurationPerFoot':143,
                 'percentObscurationPerMeter':144,
                 'percentPerSecond':99,
                 'perMinute':100,
                 'perSecond':101,
                 'psiPerDegreeFahrenheit':102,
                 'radians':103,
                 'radiansPerSecond':184,
                 'revolutionsPerMinute':104,
                 'squareMetersPerNewton':185,
                 'wattsPerMeterPerDegreeKelvin':189,
                 'wattsPerSquareMeterDegreeKelvin':141,
                 'perMille':207,
                 'gramsPerGram':208,
                 'kilogramsPerKilogram':209,
                 'gramsPerKilogram':210,
                 'milligramsPerGram':211,
                 'milligramsPerKilogram':212,
                 'gramsPerMilliliter':213,
                 'gramsPerLiter':214,
                 'milligramsPerLiter':215,
                 'microgramsPerLiter':216,
                 'gramsPerCubicMeter':217,
                 'milligramsPerCubicMeter':218,
                 'microgramsPerCubicMeter':219,
                 'nanogramsPerCubicMeter':220,
                 'gramsPerCubicCentimeter':221,
                 'wattHoursPerCubicMeter':250,
                 'joulesPerCubicMeter':251,
                 'becquerels':222,
                 'kilobecquerels':223,
                 'megabecquerels':224,
                 'gray':225,
                 'milligray':226,
                 'microgray':227,
                 'sieverts':228,
                 'millisieverts':229,
                 'microsieverts':230,
                 'microsievertsPerHour':231,
                 'decibelsA':232,
                 'nephelometricTurbidityUnit':233,
                 'pH':234,
                 'gramsPerSquareMeter':235,
                 'minutesPerDegreeKelvin':236
}


def display_devices(file_prefix=None):
    table1 = BeautifulTable()
    table2 = BeautifulTable()
    table3 = BeautifulTable()
    table4 = BeautifulTable()
    hold_table1 = BeautifulTable()
    inpt_table1 = BeautifulTable()

    table1.column_headers = ['BACnet Id', 'Name', 'IP', 'Modbus Id']
    table2.column_headers = ['BACnet Id', 'Description']
    table3.column_headers = ['BACnet Id', 'Map Name', 'Map Rev', 'Meter Name']
    table4.column_headers = ['BACnet Id', 'Modbus TO', 'COV Subscribe']
    hold_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons', 'Group gap']
    inpt_table1.column_headers = ['BACnet Id', 'Num Regs', 'WO', 'Polling', 'MB TO', 'Group Cons', 'Group gap']

    dev_list = []
    hold_reg_list = []
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
                    num_regs = len(hold_map_dict['registers'])
                    word_order = hold_map_dict.get('wordOrder', 'MUST HAVE THIS')
                    polling_time = hold_map_dict.get('pollingTime', 'MUST HAVE THIS')
                    request_timeout = hold_map_dict.get('requestTimeout', 'MUST HAVE THIS')
                    group_consecutive = hold_map_dict.get('groupConsecutive', 'MUST HAVE THIS')
                    group_gaps = hold_map_dict.get('groupGaps', 'MUST HAVE THIS')

                    hold_reg_list.append([device_instance, num_regs, word_order, polling_time, request_timeout,
                                          group_consecutive, group_gaps])

                    if file_prefix is not None:
                        pass

                else:
                    hold_reg_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

                if 'inputRegisters' in map_dict:
                    inpt_map_dict = map_dict['holdingRegisters']
                    num_regs = len(inpt_map_dict['registers'])
                    word_order = inpt_map_dict.get('wordOrder', 'MUST HAVE THIS')
                    polling_time = inpt_map_dict.get('pollingTime', 'MUST HAVE THIS')
                    request_timeout = inpt_map_dict.get('requestTimeout', 'MUST HAVE THIS')
                    group_consecutive = inpt_map_dict.get('groupConsecutive', 'MUST HAVE THIS')
                    group_gaps = inpt_map_dict.get('groupGaps', 'MUST HAVE THIS')

                    inpt_reg_list.append([device_instance, num_regs, word_order, polling_time, request_timeout,
                                          group_consecutive, group_gaps])
                else:
                    inpt_reg_list.append([map_dict['deviceInstance'], 0, '', '', '', '', ''])

            json_raw_str.close()

    dev_list.sort()
    hold_reg_list.sort()
    inpt_reg_list.sort()

    for ii in range(len(dev_list)):
        table1.append_row([dev_list[ii][0], dev_list[ii][1], dev_list[ii][2], dev_list[ii][3]])
        table2.append_row([dev_list[ii][0], dev_list[ii][4]])
        table3.append_row([dev_list[ii][0], dev_list[ii][5], dev_list[ii][6], dev_list[ii][7]])
        table4.append_row([dev_list[ii][0], dev_list[ii][8], dev_list[ii][9]])

        hold_table1.append_row(hold_reg_list[ii])
        inpt_table1.append_row(inpt_reg_list[ii])

    if len(dev_list) == 0:
        print('Nothing was found!')
    else:
        print(table1, '\n')
        print(table2, '\n')
        print(table3, '\n')
        print(table4, '\n')
        print('HOLDING REGISTERS')
        print(hold_table1, '\n')
        print('INPUT REGISTERS')
        print(inpt_table1, '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Displays info stored in meter jsons in /DeviceList directory.')

    parser.add_argument('-id', '--meter_id', type=str, default=None, help='Shows more in depth info for meter, given 2 '
                                                                          'digit id of meter')
    args = parser.parse_args()

    display_devices(file_prefix=args.meter_id)
