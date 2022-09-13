import re
import subprocess


regex = r'(?:\d+)\s\s(\d+:\d+:\d+,\d+) --> (\d+:\d+:\d+,\d+)\s\s+(.+?)(?:\r\n\r\n|$)'  # noqa: E501

compiled_regex = re.compile(regex, flags=re.DOTALL)


def offset_seconds(timeList):
    return sum(
        howmany * sec for howmany, sec in zip(
            map(int, timeList.replace(',', ':').split(':')),
            [60 * 60, 60, 1, 1e-3])
    )


def create_array_of_dict_from_srt(input_srt=None):
    transcript = [
        dict(
            startTime=offset_seconds(startTime),
            endTime=offset_seconds(endTime),
            ref=' '.join(ref.split())
        ) for startTime, endTime, ref in re.findall(
            compiled_regex, input_srt
        )
    ]
    return transcript


def extract_cc(file_obj):
    process = subprocess.Popen(
        ['ccextractor', file_obj.temporary_file_path(), '-stdout', '-quiet'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    output, errors = process.communicate()
    output = output.decode('utf-8')
    print(errors.decode('utf-8'))
    my_dict = create_array_of_dict_from_srt(output)
    return my_dict
