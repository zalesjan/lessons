import streamlit as st
import random


def select_suitable_methods(methods, total_max_duration, block_allocations):
    random.shuffle(methods)
    suitable_methods = []
    total_duration = 0
    block_count = {}
    
    # Max duration for each block
    block_durations = {block: total_max_duration * (block_allocations[block] / 100) for block in block_allocations}

    for method in methods:
        method_id, method_name, description, duration, age_group, block, subject, topic, tools, sources = method
        block = int(block)  # Ensure block is treated as an integer
        
        # Respect block time allocation and max total duration
        if block_count.get(block, 0) < 3:  # No more than 3 methods per block
            if total_duration + duration <= total_max_duration:  # Ensure overall total duration is respected
                block_remaining_duration = block_durations.get(block, 0) - block_count.get(block, 0) * duration
                
                # Ensure block-specific time limit
                if block_remaining_duration >= duration:
                    block_count[block] = block_count.get(block, 0) + 1
                    suitable_methods.append(method)
                    total_duration += duration

        if total_duration >= total_max_duration:
            break

    return suitable_methods



