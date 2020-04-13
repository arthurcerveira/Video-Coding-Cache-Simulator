import json

PARTITION_PU = {
    '0': ([1, 1],     [1, 1]),      # 2N X 2N
    '1': ([1, 0.5],   [1, 0.5]),    # 2N X N
    '2': ([0.5, 1],   [0.5, 1]),    # N X 2N
    '3': ([0.5, 0.5], [0.5, 0.5]),  # N X N
    '4': ([1, 0.75],  [1, 0.25]),   # 2N x nU
    '5': ([1, 0.25],  [1, 0.75]),   # 2N x nD
    '6': ([0.25, 1],  [0.75, 1]),   # nL x 2N
    '7': ([0.75, 1],  [0.25, 1])    # nR x 2N
}

INITIAL_CU_SHIFT = {
    '0': ([0, 0],   [0, 0]),      # 2N X 2N
    '1': ([0, 0],   [0, 0.5]),    # 2N X N
    '2': ([0, 0],   [0.5, 0]),    # N X 2N
    '3': ([0, 0],   [0.5, 0],
          [0, 0.5], [0.5, 0.5]),  # N X N
    '4': ([0, 0],   [0, 0.75]),   # 2N x nU
    '5': ([0, 0],   [0, 0.25]),   # 2N x nD
    '6': ([0, 0],   [0.25, 0]),   # nL x 2N
    '7': ([0, 0],   [0.75, 0])    # nR x 2N
}

with open('tz_cand_list.json', 'r') as fp:
    TZ_CAND_LIST = json.load(fp)


class TraceProcessor(object):
    def __init__(self):
        self.current_frame = str()
        self.ref_frame = str()

        self.cu_position = (int(), int())
        self.cu_size = int()

        self.current_ctu_postion = (int(), int())
        self.first_ctu = True

        self.first_search_shift = (int(), int())

        self.dispatcher = {
            "I ": self.start_frame,
            "L ": self.start_ctu,
            "U ": self.process_cu,
            "P ": self.process_pu,
            "C ": self.process_block,
            "F ": self.process_first_search,
            "CE": self.process_block_sequence
        }

    def process_trace(self, trace_path):
        with open(trace_path) as trace:
            for line in trace:
                key = line[0:2]

                if key in self.dispatcher:
                    yield self.dispatcher[key](line)

    def start_frame(self, line):
        # I <curr_frame_id>
        _, self.current_frame = line.split()

        return list()

    def start_ctu(self, line):
        if self.first_ctu:
            self.first_ctu = False
        else:
            x, y = self.current_ctu_postion
            yield f"W {x} {y} {self.current_frame}"

        # L <xCTU> <yCTU>
        _, x, y = line.split()

        self.current_ctu_postion = (x, y)

        return list()

    def process_cu(self, line):
        # U <xCU> <yCU> <size>
        _, x, y, cu_size = line.split()

        self.cu_size = int(cu_size)
        self.cu_position = (int(x), int(y))

        return list()

    def process_pu(self, line):
        # P <sizePU> <idPart> <ref_frame_id>
        _, size_pu, id_part, ref_frame = line.split()

        self.ref_frame = ref_frame

        partition_hor, partition_ver = PARTITION_PU[size_pu][int(id_part)]

        self.current_cu_width = int(partition_hor * self.cu_size)
        self.current_cu_height = int(partition_ver * self.cu_size)

        self.shift_cu_position(size_pu, id_part)

        return list()

    def process_block(self, line):
        # C <xCand> <yCand>
        _, x, y = line.split()

        center_x, center_y = self.cu_position

        initial_x = int(x) + int(center_x)
        initial_y = int(y) + int(center_y)

        final_x = initial_x + self.current_cu_width
        final_y = initial_y + self.current_cu_height

        for i in range(initial_y, final_y):
            for j in range(initial_x, final_x):
                yield f"R {i} {j} {self.ref_frame}"

    def process_first_search(self, line):
        # F <itID>
        _, it_id = line.split()

        lines = (TZ_CAND_LIST[it_id].split("\n"))

        center_x, center_y = self.cu_position
        shift_x, shift_y = self.first_search_shift

        # Shift CU position to First Search
        self.cu_position = (center_x + shift_x, center_y + shift_y)

        for line in lines:
            self.process_block(line)

        # Shift CU postion back to original
        self.cu_position = (center_x, center_y)

        return list()

    def process_block_sequence(self, line):
        # CE <xStart> <yStart>
        _, x, y = line.split()

        self.first_search_shift = (int(x), int(y))

        return list()

    def shift_cu_position(self, size_pu, id_part):
        x, y = self.cu_position

        x_shift, y_shift = INITIAL_CU_SHIFT[size_pu][int(id_part)]

        x = x + int(x_shift) * self.cu_size
        y = y + int(y_shift) * self.cu_size

        self.cu_position = (int(x), int(y))

        return list()


if __name__ == "__main__":
    trace_processor = TraceProcessor()
    generator = trace_processor.process_trace("samples/mem_trace.txt")

    for operations in generator:
        for operation in operations:
            print(operation)
