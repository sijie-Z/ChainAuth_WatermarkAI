"""苏州园林基础档案数据

供 init_db 与演示数据脚本共用，避免两处维护不同的园林资料。
面积单位为公顷（与联合国教科文组织申报材料口径一致）。
"""

GARDENS = [
    {
        'name': '拙政园',
        'name_en': "Humble Administrator's Garden",
        'code': 'ZZY',
        'description': '始建于明正德四年（1509），御史王献臣归隐后营建，取潘岳《闲居赋》“拙者之为政”之意。全园以水为中心，分东、中、西三部，远香堂、香洲、见山楼等景致疏朗自然，是江南私家园林的代表。',
        'location': '苏州市姑苏区东北街178号',
        'longitude': 120.6294,
        'latitude': 31.3242,
        'build_year': 1509,
        'area_size': 5.2,
        'heritage_level': '世界文化遗产',
        'heritage_year': 1997
    },
    {
        'name': '留园',
        'name_en': 'Lingering Garden',
        'code': 'LY',
        'description': '明万历二十一年（1593）徐泰时始建东园，清嘉庆年间刘恕重修称寒碧庄，光绪二年（1876）盛康购得后改今名。园以建筑空间与太湖石著称，冠云峰、五峰仙馆、林泉耆硕之馆皆为一绝。',
        'location': '苏州市姑苏区留园路338号',
        'longitude': 120.5973,
        'latitude': 31.3226,
        'build_year': 1593,
        'area_size': 2.33,
        'heritage_level': '世界文化遗产',
        'heritage_year': 1997
    },
    {
        'name': '狮子林',
        'name_en': 'Lion Grove Garden',
        'code': 'SZL',
        'description': '元至正二年（1342）天如禅师创建，因园内湖石多形似狮子而得名。假山群洞壑宛转、上下三层，素有“假山王国”之誉，倪瓒曾参与造园并绘《狮子林图》。',
        'location': '苏州市姑苏区园林路23号',
        'longitude': 120.6286,
        'latitude': 31.3246,
        'build_year': 1342,
        'area_size': 0.88,
        'heritage_level': '世界文化遗产',
        'heritage_year': 2000
    },
    {
        'name': '网师园',
        'name_en': 'Master of the Nets Garden',
        'code': 'WSY',
        'description': '始建于南宋淳熙年间，原为史正志万卷堂故址；清乾隆年间宋宗元重筑，取“渔隐”之意名网师园。园小而精，殿春簃、月到风来亭、濯缨水阁布局紧凑，被誉为“小园极则”。',
        'location': '苏州市姑苏区带城桥路阔家头巷11号',
        'longitude': 120.6261,
        'latitude': 31.3052,
        'build_year': 1174,
        'area_size': 0.6,
        'heritage_level': '世界文化遗产',
        'heritage_year': 1997
    },
    {
        'name': '沧浪亭',
        'name_en': 'Canglang Pavilion',
        'code': 'CLT',
        'description': '北宋庆历五年（1045）苏舜钦以四万钱购得废园，临水筑亭，取《楚辞·渔父》“沧浪之水清兮”命名。园以复廊漏窗借景著称，是苏州现存最古老的园林。',
        'location': '苏州市姑苏区人民路沧浪亭街3号',
        'longitude': 120.6269,
        'latitude': 31.3006,
        'build_year': 1045,
        'area_size': 1.08,
        'heritage_level': '世界文化遗产',
        'heritage_year': 2000
    },
    {
        'name': '耦园',
        'name_en': "Couple's Retreat Garden",
        'code': 'OY',
        'description': '清初为陆锦涉园故址，同治十三年（1874）沈秉成购得并扩建，因夫妇偕隐、东西两园相对而名“耦园”。三面临河，一宅两园，黄石假山与受月池相映成趣。',
        'location': '苏州市姑苏区小新桥巷6号',
        'longitude': 120.6350,
        'latitude': 31.3208,
        'build_year': 1874,
        'area_size': 0.79,
        'heritage_level': '世界文化遗产',
        'heritage_year': 2000
    },
    {
        'name': '艺圃',
        'name_en': 'Garden of Cultivation',
        'code': 'YP',
        'description': '明嘉靖二十年（1541）袁祖庚始建醉颖堂，后归文震孟名药圃，清初姜埰隐居于此改称艺圃。全园以博雅堂、延光阁与浴鸥池为核心，简练疏朗，为明代园林遗构。',
        'location': '苏州市姑苏区文衙弄5号',
        'longitude': 120.6135,
        'latitude': 31.3155,
        'build_year': 1541,
        'area_size': 0.38,
        'heritage_level': '世界文化遗产',
        'heritage_year': 2000
    },
    {
        'name': '环秀山庄',
        'name_en': 'Mountain Villa with Embracing Beauty',
        'code': 'HXSZ',
        'description': '原为晋代景德寺旧址，清乾隆年间为毕沅宅园，道光二十七年（1847）汪氏重修。园中湖石假山出自叠山名家戈裕良之手，咫尺之间具千岩万壑之势。',
        'location': '苏州市姑苏区景德路272号',
        'longitude': 120.6157,
        'latitude': 31.3118,
        'build_year': 1847,
        'area_size': 0.22,
        'heritage_level': '世界文化遗产',
        'heritage_year': 1997
    },
    {
        'name': '怡园',
        'name_en': 'Joyous Garden',
        'code': 'YY',
        'description': '清同治十三年（1874）至光绪八年，顾文彬父子耗时九年建成。园中复廊、鸳鸯厅、石舫等兼采苏州诸园之长，并以书条石集帖著称。',
        'location': '苏州市姑苏区人民路343号',
        'longitude': 120.6181,
        'latitude': 31.3092,
        'build_year': 1874,
        'area_size': 0.6,
        'heritage_level': '市级文保单位'
    },
    {
        'name': '可园',
        'name_en': 'Keyuan Garden',
        'code': 'KY',
        'description': '清雍正年间始建，乾隆年间为苏州正谊书院园林，是苏州现存唯一的书院园林。园以水池为中心，挹清堂、浩歌亭与学古堂相望，与沧浪亭隔水成对景。',
        'location': '苏州市姑苏区人民路708号',
        'longitude': 120.6275,
        'latitude': 31.3003,
        'build_year': 1723,
        'area_size': 0.5,
        'heritage_level': '市级文保单位'
    }
]
