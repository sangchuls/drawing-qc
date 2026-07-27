import json, re, sys

with open('outputs/extracted.json', encoding='utf-8') as f:
    data = json.load(f)

p1 = [d for d in data if d['page'] == 1]
full_pat = re.compile(r'^[A-Z]{1,2}-\d{2,4}$')
fulls = set(t['text'] for t in p1 if full_pat.match(t['text']))
prefixes = [t for t in p1 if re.match(r'^[A-Z]{1,2}-$', t['text']) and t['x'] > 35]
paired = set()
for p in prefixes:
    cands = [t for t in p1 if re.match(r'^\d{2,4}$', t['text']) and abs(t['x']-p['x']) < 5 and 0 < (t['y']-p['y']) < 20]
    if cands:
        best = min(cands, key=lambda t: t['y']-p['y'])
        paired.add(p['text']+best['text'])
listed = fulls | paired

own = {'A-001','A-001a','A-002','A-003','A-010'}
for n in ['021','022','023','024','025','026','027','031','041','042','051','052','053','054','055','056','057','058','059',
          '061','062','063','064','065','066','067','068','071','072','073','074','075','076','077','078',
          '081','082','083','084','091','092','093','094','095','096','097',
          '101','102','103','104','105','106','107','108','109','110','111','112','113','114','115','116','117',
          '201','202','203','204','205','301','302','303','304','305','306','307','308','309','310','311','312']:
    own.add('A-'+n)

missing = sorted(listed - own, key=lambda s: (len(s), s))
extra_in_own_not_listed = sorted(own - listed, key=lambda s: (len(s), s))

with open(sys.argv[1], 'w', encoding='utf-8') as f:
    f.write(f"listed_total={len(listed)}\nown_total={len(own)}\n")
    f.write(f"missing_count={len(missing)}\n")
    f.write("missing:\n" + ', '.join(missing) + "\n\n")
    f.write("in_own_but_not_in_index_list (informational):\n" + ', '.join(extra_in_own_not_listed) + "\n")
