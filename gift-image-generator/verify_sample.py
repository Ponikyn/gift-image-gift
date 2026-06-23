from generate_images import parse_gift
from pathlib import Path
sample = Path('verify_sample.gift')
text = '''\\r\\n</br>
<img src\\="@@PLUGINFILE@@/Image/q003.png">{
=<img src\\="@@PLUGINFILE@@/Image/q003_ans01.png">
=<img src\\="@@PLUGINFILE@@/Image/q003_ans02.png">
=<img src\\="@@PLUGINFILE@@/Image/q003_ans03.png">
=<img src\\="@@PLUGINFILE@@/Image/q003_ans04.png">
}

Ќайдите общую точность модели. (точность из теории веро€тности) { =0.7 =70% }

Ќайдите точность предсказани€ положительного класса. (точность из теории веро€тности) { =0.6 =60% }

Ќайдите точность предсказани€ отрицательного класса. (точность из теории веро€тности) { =0.1 =10% }

Ќайдите веро€тность ошибки { =0.3 =30% }
'''
sample.write_text(text, encoding='utf-8')
qs = parse_gift(str(sample))
print('items:', len(qs))
for idx,item in enumerate(qs,1):
    print('--- item', idx, 'type', item['type'], 'keep_raw', item.get('keep_answers_raw'))
    if item['type'] == 'question':
        print('question=', repr(item.get('question')))
        print('raw_block=', repr(item.get('raw_block')))
        print('raw_answers=', repr(item.get('raw_answers')))
        print('answers=', item.get('answers'))
    else:
        print('raw=', repr(item.get('raw')))
