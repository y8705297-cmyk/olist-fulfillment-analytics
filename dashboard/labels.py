"""Chinese display labels keyed by the existing Portuguese category keys."""

OVERVIEW = "经营与履约概览"
DIAGNOSTICS = "履约异常诊断"
EXPERIENCE = "客户体验分析"
SELLERS = "商家排查优先级"
SCENARIOS = "改善情景测算"

ORDERS = "订单数"
ELIGIBLE = "可判定延误订单数"
LATE_ORDERS = "延误订单数"
LATE_RATE = "配送延误率"
LOW_RATE = "低评分率"
MONTH = "下单月份"
STATE = "收货州"
CATEGORY = "订单主品类"
HANDOFF = "下单至交接承运方"
TRANSIT = "交接承运方至签收"
ON_TIME = "按期"
LATE = "延误"
OR = "优势比（OR）"

CATEGORY_NAMES = {
    "(unknown)": "未分类",
    "agro_industria_e_comercio": "农业工商业",
    "alimentos": "食品",
    "alimentos_bebidas": "食品与饮料",
    "artes": "艺术用品",
    "artes_e_artesanato": "艺术与手工艺品",
    "artigos_de_festas": "派对用品",
    "artigos_de_natal": "圣诞用品",
    "audio": "音频设备",
    "automotivo": "汽车用品",
    "bebes": "母婴用品",
    "bebidas": "饮料",
    "beleza_saude": "美妆与健康",
    "brinquedos": "玩具",
    "cama_mesa_banho": "床品、桌布与浴室用品",
    "casa_conforto": "舒适家居",
    "casa_conforto_2": "舒适家居（二）",
    "casa_construcao": "家居建材",
    "cds_dvds_musicais": "音乐光盘与影音光碟",
    "cine_foto": "影视与摄影",
    "climatizacao": "空调与温控设备",
    "consoles_games": "游戏主机与游戏",
    "construcao_ferramentas_construcao": "施工与建筑工具",
    "construcao_ferramentas_ferramentas": "工程通用工具",
    "construcao_ferramentas_iluminacao": "施工照明",
    "construcao_ferramentas_jardim": "工程园艺工具",
    "construcao_ferramentas_seguranca": "施工防护用品",
    "cool_stuff": "创意好物",
    "dvds_blu_ray": "影视光碟",
    "eletrodomesticos": "家用电器",
    "eletrodomesticos_2": "家用电器（二）",
    "eletroportateis": "便携小家电",
    "eletronicos": "电子产品",
    "esporte_lazer": "体育与休闲",
    "fashion_bolsas_e_acessorios": "箱包与时尚配饰",
    "fashion_calcados": "时尚鞋履",
    "fashion_esporte": "运动服饰",
    "fashion_roupa_feminina": "女装",
    "fashion_roupa_infanto_juvenil": "儿童与青少年服装",
    "fashion_roupa_masculina": "男装",
    "fashion_underwear_e_moda_praia": "内衣与沙滩服饰",
    "ferramentas_jardim": "园艺工具",
    "flores": "花卉",
    "fraldas_higiene": "纸尿裤与卫生用品",
    "industria_comercio_e_negocios": "工商业用品",
    "informatica_acessorios": "电脑配件",
    "instrumentos_musicais": "乐器",
    "la_cuisine": "烹饪用品",
    "livros_importados": "进口图书",
    "livros_interesse_geral": "大众图书",
    "livros_tecnicos": "专业技术图书",
    "malas_acessorios": "行李箱与配件",
    "market_place": "平台综合商品",
    "moveis_colchao_e_estofado": "床垫与软体家具",
    "moveis_cozinha_area_de_servico_jantar_e_jardim": "厨房、家务区、餐厅与花园家具",
    "moveis_decoracao": "家具与装饰",
    "moveis_escritorio": "办公家具",
    "moveis_quarto": "卧室家具",
    "moveis_sala": "客厅家具",
    "musica": "音乐",
    "papelaria": "文具",
    "pc_gamer": "游戏电脑",
    "pcs": "台式电脑",
    "perfumaria": "香水香氛",
    "pet_shop": "宠物用品",
    "portateis_casa_forno_e_cafe": "家用、烘焙与咖啡小电器",
    "portateis_cozinha_e_preparadores_de_alimentos": "厨房小电器与食物加工设备",
    "relogios_presentes": "钟表与礼品",
    "seguros_e_servicos": "保险与服务",
    "sinalizacao_e_seguranca": "标识与安防",
    "tablets_impressao_imagem": "平板电脑、打印与影像设备",
    "telefonia": "通信设备",
    "telefonia_fixa": "固定电话",
    "utilidades_domesticas": "家居日用品",
}


def category_name(key):
    return CATEGORY_NAMES.get(key, f"其他品类（{key}）")
