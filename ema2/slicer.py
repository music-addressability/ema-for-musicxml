import xml.etree.ElementTree as ET
from ema2.emaexpfull import EmaExpFull, ema_to_list


def convert_to_rest(note: ET.Element):
    """ Remove all note-associated attributes, (i.e. keep duration, type, voice, and lyrics). """
    note_remove = ["pitch", "stem"]
    for r in note_remove:
        note_elem = note.find(r)
        if note_elem:
            note.remove(note_elem)
    note.insert(0, ET.Element("rest"))


def slice_score(tree: ET.ElementTree, ema_exp_full: EmaExpFull):
    """ For part-wise MusicXML files. """
    staves = tree.findall("part")
    for s in range(len(staves)):
        process_stave(ema_exp_full, s+1, staves[s])
    remove_blank_staves(tree, ema_exp_full)
    return tree

# TODO: keep track of selected element ids
# if does not have id, get an xpath, either way both of them are a string
def process_stave(ema_exp_full, staff_num, measures):
    """ Traverse one stave and edit it according to the EmaExpFull. """
    selection = ema_exp_full.selection
    m = 0
    attrib = {}
    insert_attrib = {}
    while m < len(measures):
        measure = measures[m]
        measure_num = measure.attrib['number']

        # Keep track of attribute changes - e.g. if we don't select a measure with a time sig change,
        # we would still want the new time sig to be reflected in following measures.
        m_attr_elem = measure.find('attributes')
        if m_attr_elem:
            measure_attrib = elem_to_dict(m_attr_elem)
            for key in measure_attrib:
                attrib[key] = measure_attrib[key]
                if measure_num not in selection:
                    insert_attrib[key] = measure_attrib[key]

        # make selection
        if measure_num in selection:
            if insert_attrib: # True if insert_attrib != {}
                measure.insert(0, dict_to_elem('attributes', insert_attrib))
                insert_attrib = {}

            ema_measure = selection[measure_num]
            if staff_num in ema_measure:
                numer = int(attrib['time']['beats']['text'])
                denom = int(attrib['time']['beat-type']['text'])
                beat_factor = numer / denom
                divisions = int(attrib['divisions']['text'])
                # TODO: Handle cut time?
                # TODO: beats can be floats; when rewriting make sure beats in in sorted order
                # TODO: sort by starting time - do not allow overlapping ranges
                ema_beats = ema_measure[staff_num] # list of EmaRange
                ema_index = 0
                curr_beat = 1
                # Addressing by note should be better because of completeness considerations later
                for note in measure.findall("note"):
                    duration = int(note.find("duration").text) / (beat_factor * divisions)
                    beat_range = ema_beats[ema_index]

                    if beat_range.end != 'end':
                        while curr_beat > beat_range.end:
                            ema_index += 1
                            beat_range = ema_beats[ema_index]

                    if not (val_in_range(curr_beat, beat_range) or val_in_range(curr_beat + duration, beat_range)):
                        convert_to_rest(note)
                    curr_beat += duration
            else:
                for note in measure.findall("note"):
                    convert_to_rest(note)
            m += 1
        else:
            measures.remove(measure)
    # TODO: Last measure in stave should have single "\n" tail, not two - not sure if this will cause any problems.


def val_in_range(val, ema_range):
    s = ema_range.start == 'start' or val >= ema_range.start
    e = ema_range.end == 'end' or val <= ema_range.end
    return s and e

def remove_blank_staves(tree, ema_exp_full):
    selected_staves = ema_exp_full.selected_staves
    staves = tree.findall("part")
    partlist = tree.find("part-list")
    scoreparts = partlist.findall("score-part")
    for s in range(len(staves) - 1, -1, -1):
        staff_num = s + 1
        if staff_num not in selected_staves:
            tree.getroot().remove(staves[s])
            partlist.remove(scoreparts[s])


# Used to convert the 'attributes' element to a dict for easy value access during beat slicing.
def elem_to_dict(elem):
    d = {'text': elem.text, 'tail': elem.tail}
    if elem:
        for child in elem:
            d[child.tag] = elem_to_dict(child)
    return d


def dict_to_elem(name, d):
    elem = ET.Element(name)
    elem.text = d['text']
    elem.tail = d['tail']
    for key in d:
        if key != 'text' and key != 'tail':
            elem.append(dict_to_elem(key, d[key]))
    return elem
