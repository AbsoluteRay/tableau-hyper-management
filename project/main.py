import csv
import getopt
import sys
import time

from datetime import datetime,timedelta

from tableauhyperapi import HyperProcess, Telemetry, \
    Connection, CreateMode, \
    NOT_NULLABLE, NULLABLE, SqlType, TableDefinition, \
    Inserter, \
    escape_name, escape_string_literal, \
    TableName, \
    HyperException, \
    Timestamp

from TypeDetermination import TypeDetermination


def build_hyper_columns_for_csv(given_file_name, csv_field_separator, detected_csv_structure, verbose):
    hyper_table_columns_to_return = []
    for crt_field_structure in detected_csv_structure:
        hyper_table_columns_to_return.append(crt_field_structure['order'])
        current_column_type=convert_to_hyper_types(crt_field_structure['type'])
        if verbose:
            print('Column ' + str(crt_field_structure['order']) + ' having name "'
                + crt_field_structure['name'] + '" and type "' 
                + crt_field_structure['type'] + '" will become "'
                + str(current_column_type) + '"')
        hyper_table_columns_to_return[crt_field_structure['order']] = TableDefinition.Column(
            name=crt_field_structure['name'],
            type=current_column_type,
            nullability=NULLABLE
        )
    return hyper_table_columns_to_return


def command_line_argument_interpretation(argv):
    input_file = ''
    csv_field_separator = ''
    schema_name = ''
    table_name = ''
    output_file = ''
    verbose = False
    print('#'*120)
    try:
        opts, args = getopt.getopt(argv, "hi:cfs:sn:tn:o:v:", [
            "input-file=", 
            "csv-field-separator=", 
            "schema-name=", 
            "table-name=", 
            "output-file=",
            "verbose"
        ])
    except getopt.GetoptError:
        print('main.py -i|--input-file <input-file>'
            + ' -cfs|--csv-field-separator <csv-field-separator>'
            + ' [-sn|--schema-name <schema-name>]'
            + ' -tn|--table-name <table-name>'
            + ' -o|--output-file <output-file>'
            + ' [-v|--verbose]'
        )
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('main.py -i|--input-file <input-file>'
            + ' -cfs|--csv-field-separator <csv-field-separator>'
            + ' [-sn|--schema-name <schema-name>]'
            + ' -tn|--table-name <table-name>'
            + ' -o|--output-file <output-file>')
            sys.exit()
        elif opt in ("-i", "--input-file"):
            input_file = arg
        elif opt in ("-cfs", "--csv-field-separator"):
            csv_field_separator = arg
        elif opt in ("-sn", "--schema-name"):
            schema_name = arg
        elif opt in ("-tn", "--table-name"):
            table_name = arg
        elif opt in ("-o", "--output-file"):
            output_file = arg
        elif opt in ("-v", "--verbose"):
            verbose = True
        else:
            assert False, "unhandled option"
    if input_file == '':
        print('Fatal Error.....................................................................:-(')
        print('Expected -i|--input-file <input-file> but nothing of that sort has been seen... :-(')
        sys.exit(2)
    else:
        print('Input file is "' + input_file + '"')
    if csv_field_separator == '':
        print('Fatal Error........................................................................................:-(')
        print('Expected -cs|--csv-field-separator <csv-field-separator> but nothing of that sort has been seen... :-(')
        sys.exit(2)
    else:
        print('CSV field separator is "' + csv_field_separator + '"')
    if table_name == '':
        print('Fatal Error......................................................................:-(')
        print('Expected -tn|--table-name <table-name> but nothing of that sort has been seen... :-(')
        sys.exit(2)
    else:
        print('Table name is "' + table_name + '"')
    if output_file == '':
        print('Fatal Error.......................................................................:-(')
        print('Expected -o|--output-file <output-file> but nothing of that sort has been seen... :-(')
        sys.exit(2)
    else:
        print('Output file is "' + output_file + '"')
    # marking the start of performance measuring (in nanoseconds)
    performance_start = time.perf_counter_ns()
    print('#'*120)
    run_create_hyper_file_from_csv(input_file,
                                   csv_field_separator,
                                   schema_name,
                                   table_name,
                                   output_file,
                                   verbose)    
    performance_finish = time.perf_counter_ns()
    performance_timed = timedelta(microseconds=(performance_finish - performance_start)/1000)
    print("This script has been executed in " + format(performance_timed) + ' seconds')


def convert_to_hyper_types(given_type):
    switcher = {
        'empty': SqlType.text(),
        'int': SqlType.big_int(),
        'float-US': SqlType.double(),
        'date-iso8601': SqlType.date(),
        'time24': SqlType.time(),
        'timeUS': SqlType.time(),
        'datetime-iso8601': SqlType.timestamp(),
        'str': SqlType.text()
    }
    return switcher.get(given_type)


def detect_csv_structure(given_file_name, csv_field_separator, verbose):
    csv_structure = []
    with open(given_file_name, newline='') as csv_file:
        csv_object = csv.DictReader(csv_file, delimiter=';')
        # parse rows with index
        for row_idx, row_content in enumerate(csv_object):
            # limit rows evaluation to a certain value
            if row_idx <= 200:
                print_prefix = 'On the row ' + str((row_idx + 1))
                # parse all columns with index
                for col_idx, column_name in enumerate(csv_object.fieldnames):
                    # determine the field type by current row and column content
                    crt_field_type = TypeDetermination.type_determination(row_content[csv_object.fieldnames[col_idx]])
                    # evaluate if CSV structure for current field (column) already exists
                    if row_idx > 0:
                        # if CSV structure for current field (column) exists, does the current type is more important?
                        crt_type_index = TypeDetermination.importance__low_to_high.index(crt_field_type)
                        prv_type_index = TypeDetermination.importance__low_to_high.index(csv_structure[col_idx]['type'])
                        if crt_type_index > prv_type_index:
                            if verbose:
                                print(print_prefix 
                                    + ' column ' + str(col_idx)
                                    + ' having the name [' + csv_object.fieldnames[col_idx] + '] '
                                    + ' has the value <' + row_content[csv_object.fieldnames[col_idx]]
                                    + '> which means is of type "' + crt_field_type + '" '
                                    + ' and that is stronger than previously thought to be as "'
                                    + csv_structure[col_idx]['type'] + '"')
                            csv_structure[col_idx]['type'] = crt_field_type
                    else:
                        csv_structure.append(col_idx)
                        csv_structure[col_idx] = {
                            'order': col_idx,
                            'name': csv_object.fieldnames[col_idx],
                            'type': crt_field_type
                        }
                        if crt_field_type == 'str':
                            csv_structure[col_idx]['length'] = len(row_content[csv_object.fieldnames[col_idx]])
                        if verbose:
                            print(print_prefix + ' column ' + str(col_idx)
                                + ' having the name [' + csv_object.fieldnames[col_idx] + '] '
                                + ' has the value <' + row_content[csv_object.fieldnames[col_idx]]
                                + '> which mean is of type "' + crt_field_type + '"')
        return csv_structure


def rebuild_csv_content_for_hyper(given_file_name, csv_field_separator, detected_fields_type, verbose):
    csv_content_for_hyper = []
    with open(given_file_name, newline='') as csv_file:
        csv_object = csv.DictReader(csv_file, delimiter=csv_field_separator)
        # parse rows with index
        for row_idx, row_content in enumerate(csv_object):
            csv_content_for_hyper.append(row_idx)
            csv_content_for_hyper[row_idx] = []
            print_prefix = 'On the row ' + str((row_idx + 1))
            # parse all columns with index
            for col_idx, column_name in enumerate(csv_object.fieldnames):
                csv_content_for_hyper[row_idx].append(col_idx)
                if row_content[csv_object.fieldnames[col_idx]] == '':
                    csv_content_for_hyper[row_idx][col_idx] = None
                else:
                    if detected_fields_type[col_idx]['type'] == 'datetime-iso8601':
                        tm = datetime.fromisoformat(row_content[csv_object.fieldnames[col_idx]])
                        csv_content_for_hyper[row_idx][col_idx] = Timestamp(tm.year, tm.month, tm.day,
                                                                   tm.hour, tm.minute, tm.second)
                    elif detected_fields_type[col_idx]['type'] == 'int':
                        csv_content_for_hyper[row_idx][col_idx] = int(row_content[csv_object.fieldnames[col_idx]])
                    elif detected_fields_type[col_idx]['type'] == 'float-US':
                        csv_content_for_hyper[row_idx][col_idx] = float(row_content[csv_object.fieldnames[col_idx]])
                    else:
                        csv_content_for_hyper[row_idx][col_idx] = row_content[csv_object.fieldnames[col_idx]].\
                            replace('"', '\\"')
                if verbose:
                    print(print_prefix + ' column ' + str(col_idx)
                        + ' having the name [' + csv_object.fieldnames[col_idx] + '] '
                        + ' has the value <' + row_content[csv_object.fieldnames[col_idx]]
                        + '> which was interpreted as <<' + str(csv_content_for_hyper[row_idx][col_idx]) + '>>')
    return csv_content_for_hyper


def run_create_hyper_file_from_csv(input_csv_file,
                                   csv_field_separator,
                                   schema_name,
                                   table_name,
                                   output_hyper_file,
                                   verbose):
    detected_csv_structure = detect_csv_structure(input_csv_file,
                                                  csv_field_separator,
                                                  verbose)
    hyper_table_columns = build_hyper_columns_for_csv(input_csv_file,
                                                      csv_field_separator,
                                                      detected_csv_structure,
                                                      verbose)
    # Starts the Hyper Process with telemetry enabled/disabled to send data to Tableau or not
    # To opt in, simply set telemetry=Telemetry.SEND_USAGE_DATA_TO_TABLEAU.
    # To opt out, simply set telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU.
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        # Creates new Hyper file <output_hyper_file>
        # Replaces file with CreateMode.CREATE_AND_REPLACE if it already exists.
        with Connection(endpoint=hyper.endpoint,
                        database=output_hyper_file,
                        create_mode=CreateMode.CREATE_AND_REPLACE) as hyper_connection:
            if schema_name == '':
                hyper_table = TableDefinition(
                    name=table_name,
                    columns=hyper_table_columns
                )
            else:
                hyper_connection.catalog.create_schema(schema_name)
                hyper_table = TableDefinition(
                    name=TableName(schema_name, table_name),
                    columns=hyper_table_columns
                )
            hyper_connection.catalog.create_table(table_definition=hyper_table)
            print("The connection to the Hyper file has been created.")
            '''
            VERDICT: does not work as DOUBLE or INT are not accepting empty values... :-(
            print("I am about to execute command: " 
                + f"COPY {hyper_table.table_name} from {escape_string_literal(input_csv_file)} with "
                f"(format csv, NULL 'NULL', delimiter '{csv_field_separator}', header)")
            # Load all rows into "Customers" table from the CSV file.
            # `execute_command` executes a SQL statement and returns the impacted row count.
            count_in_target_table = hyper_connection.execute_command(
                command=f"COPY {hyper_table.table_name} from {escape_string_literal(input_csv_file)} with "
                f"(format csv, NULL 'NULL', delimiter '{csv_field_separator}', header)")
            print(f"The number of rows in table {hyper_table.table_name} is {count_in_target_table}.")
            '''
            # The rows to insert into the <hyper_table> table.
            data_to_insert = rebuild_csv_content_for_hyper(input_csv_file, 
                                                           csv_field_separator,
                                                           detected_csv_structure,
                                                           verbose)
            # Execute the actual insert
            with Inserter(hyper_connection, hyper_table) as hyper_inserter:
                hyper_inserter.add_rows(rows=data_to_insert)
                hyper_inserter.execute()
            # Number of rows in the <hyper_table> table.
            # `execute_scalar_query` is for executing a query that returns exactly one row with one column.
            row_count = hyper_connection.execute_scalar_query(query=f"SELECT COUNT(*) FROM {hyper_table.table_name}")
            print(f"The number of rows in table {hyper_table.table_name} is {row_count}.")
        print("The connection to the Hyper file has been closed.")
    print("The Hyper process has been shut down.")


if __name__ == '__main__':
    try:
        command_line_argument_interpretation(sys.argv[1:])
    except HyperException as ex:
        print(ex)
        exit(1)
