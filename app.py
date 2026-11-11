import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import json
import random
import os

st.set_page_config(page_title="WMS 3D - Central de Operações", layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------
# ESTILIZAÇÃO CSS CUSTOMIZADA (LIGHT THEME MODERN)
# ---------------------------------------------------------
st.markdown("""
<style>
    .stApp { background-color: #f3f4f6; color: #111827; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. GERENCIAMENTO DE ESTADO COM PERSISTÊNCIA COMPARTILHADA
# ---------------------------------------------------------
ESTADO_ARQUIVO = "wms_estado.json"

def carregar_estoque():
    if os.path.exists(ESTADO_ARQUIVO):
        try:
            return pd.read_json(ESTADO_ARQUIVO, dtype={"nf": str})
        except Exception:
            pass
    
    dados_iniciais = []
    niveis = [10, 20, 30]
    
    def get_pairs(start, count):
        return [(start + i*4, start + i*4 + 2) for i in range(count)]
    
    racks_c_trat = get_pairs(200, 4)   
    racks_c_geral = get_pairs(216, 15) 
    
    racks_b_trat = get_pairs(101, 4)   
    racks_b_geral = get_pairs(117, 14) 
    
    racks_a_trat = get_pairs(100, 4)   
    racks_a_geral = get_pairs(116, 14) 

    def montar_rua(nome_rua, lista_trat, lista_geral, z_pos, offset_geral):
        for idx, (pos_r, pos_l) in enumerate(lista_trat):
            col_idx = idx
            for nivel in niveis:
                dados_iniciais.append({
                    "id": f"R-{nome_rua}-{pos_r}-{nivel}", "rua": nome_rua, "pos_num": pos_r, "nivel": nivel,
                    "col_idx": col_idx, "side": "right", "z_pos": z_pos, "zona": "Tratativa",
                    "status": "Vazio", "etiqueta": "", "nf": "", "remetente": "", "volumes": 0
                })
                dados_iniciais.append({
                    "id": f"R-{nome_rua}-{pos_l}-{nivel}", "rua": nome_rua, "pos_num": pos_l, "nivel": nivel,
                    "col_idx": col_idx, "side": "left", "z_pos": z_pos, "zona": "Tratativa",
                    "status": "Vazio", "etiqueta": "", "nf": "", "remetente": "", "volumes": 0
                })
        
        for idx, (pos_r, pos_l) in enumerate(lista_geral):
            col_idx = idx + offset_geral
            for nivel in niveis:
                # Define setor Duracell (Nível 10, Rua A de 116 a 146, Rua B de 117 a 147)
                zona = "Armazém"
                if nivel == 10:
                    if nome_rua == "A" and 116 <= pos_r <= 146:
                        zona = "Duracell"
                    elif nome_rua == "B" and 117 <= pos_r <= 147:
                        zona = "Duracell"

                dados_iniciais.append({
                    "id": f"R-{nome_rua}-{pos_r}-{nivel}", "rua": nome_rua, "pos_num": pos_r, "nivel": nivel,
                    "col_idx": col_idx, "side": "right", "z_pos": z_pos, "zona": zona,
                    "status": "Vazio", "etiqueta": "", "nf": "", "remetente": "", "volumes": 0
                })
                dados_iniciais.append({
                    "id": f"R-{nome_rua}-{pos_l}-{nivel}", "rua": nome_rua, "pos_num": pos_l, "nivel": nivel,
                    "col_idx": col_idx, "side": "left", "z_pos": z_pos, "zona": zona,
                    "status": "Vazio", "etiqueta": "", "nf": "", "remetente": "", "volumes": 0
                })

    montar_rua("C", racks_c_trat, racks_c_geral, z_pos=-8.0, offset_geral=4)
    montar_rua("B", racks_b_trat, racks_b_geral, z_pos=-0.7, offset_geral=5)
    montar_rua("A", racks_a_trat, racks_a_geral, z_pos=0.7, offset_geral=5)

    df_init = pd.DataFrame(dados_iniciais)
    df_init.to_json(ESTADO_ARQUIVO, orient="records", force_ascii=False)
    return df_init

def salvar_estoque(df):
    df.to_json(ESTADO_ARQUIVO, orient="records", force_ascii=False)

if "estoque" not in st.session_state:
    st.session_state.estoque = carregar_estoque()

df = st.session_state.estoque

# ---------------------------------------------------------
# 2. METRICAS / DASHBOARD DE CABEÇALHO
# ---------------------------------------------------------
st.title("🏭 WMS 3D - Central de Operações")

total_pos = len(df)
ocupados_total = len(df[df["status"] == "Ocupado"])
taxa_ocupacao = (ocupados_total / total_pos * 100) if total_pos > 0 else 0
ocupados_tratativa = len(df[(df["status"] == "Ocupado") & (df["zona"] == "Tratativa")])
ocupados_duracell = len(df[(df["status"] == "Ocupado") & (df["zona"] == "Duracell")])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total de Posições", total_pos)
m2.metric("Ocupação Geral", f"{taxa_ocupacao:.1f}%", f"{ocupados_total} paletes")
m3.metric("Duracell Ocupado", f"{ocupados_duracell} paletes")
m4.metric("Tratativa Ocupada", f"{ocupados_tratativa} paletes")

st.divider()

# ---------------------------------------------------------
# 3. PAINEL LATERAL (IMPORTAÇÃO DE EXCEL & ALOCAÇÃO MANUAL)
# ---------------------------------------------------------
st.sidebar.title("📦 Integração & Alocação")

with st.sidebar.expander("📂 Importar Relatório Excel", expanded=True):
    arquivo_excel = st.file_uploader("Envie a planilha (.xlsx)", type=["xlsx"])
    
    if arquivo_excel is not None:
        if "arquivo_processado" not in st.session_state or st.session_state.arquivo_processado != arquivo_excel.name:
            try:
                # Coluna 'Número' corresponde às Notas Fiscais (Coluna F)
                colunas_necessarias = ["Posição", "Número", "Remetente", "Volumes"]
                df_excel = pd.read_excel(arquivo_excel, usecols=lambda col: col in colunas_necessarias)
                
                st.session_state.estoque["status"] = "Vazio"
                st.session_state.estoque["etiqueta"] = ""
                st.session_state.estoque["nf"] = ""
                st.session_state.estoque["remetente"] = ""
                st.session_state.estoque["volumes"] = 0
                
                valid_ids = set(st.session_state.estoque["id"])
                df_excel = df_excel[df_excel["Posição"].isin(valid_ids)].copy()
                
                def clean_nf(val):
                    if pd.isna(val): return ""
                    try:
                        f = float(val)
                        if f.is_integer(): return str(int(f))
                    except:
                        pass
                    return str(val).strip()

                df_excel['clean_nf'] = df_excel['Número'].apply(clean_nf)
                
                df_agrupado = df_excel.groupby('Posição').agg({
                    'clean_nf': lambda x: ', '.join(sorted(list(set([str(v) for v in x.dropna() if str(v) != 'nan' and str(v) != ''])))),
                    'Remetente': lambda x: ', '.join(sorted(list(set([str(v).strip() for v in x.dropna() if str(v) != 'nan' and str(v) != ''])))),
                    'Volumes': 'sum'
                }).reset_index()
                
                contador_atualizados = 0
                for _, row in df_agrupado.iterrows():
                    pos_excel = str(row["Posição"]).strip()
                    if pos_excel in valid_ids:
                        idx_wms = st.session_state.estoque[st.session_state.estoque["id"] == pos_excel].index
                        if len(idx_wms) > 0:
                            i = idx_wms[0]
                            st.session_state.estoque.at[i, "status"] = "Ocupado"
                            st.session_state.estoque.at[i, "nf"] = str(row["clean_nf"])
                            st.session_state.estoque.at[i, "remetente"] = str(row["Remetente"])
                            st.session_state.estoque.at[i, "volumes"] = int(row["Volumes"]) if pd.notna(row["Volumes"]) else 0
                            st.session_state.estoque.at[i, "etiqueta"] = f"PAL-{random.randint(1000, 9999)}"
                            contador_atualizados += 1
                
                salvar_estoque(st.session_state.estoque)
                st.session_state.arquivo_processado = arquivo_excel.name
                st.success(f"Relatório importado! {contador_atualizados} posições mapeadas.")
            except Exception as e:
                st.error(f"Erro ao processar a planilha: {e}")

with st.sidebar.expander("💾 Backup e Restauração", expanded=False):
    json_bytes = st.session_state.estoque.to_json(orient="records", force_ascii=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Backup do Armazém",
        data=json_bytes,
        file_name="wms_backup.json",
        mime="application/json",
        use_container_width=True
    )
    
    arquivo_backup = st.file_uploader("📤 Restaurar Backup (.json)", type=["json"])
    if arquivo_backup is not None:
        try:
            df_restaurado = pd.read_json(arquivo_backup, dtype={"nf": str})
            if "id" in df_restaurado.columns and "status" in df_restaurado.columns:
                st.session_state.estoque = df_restaurado
                salvar_estoque(df_restaurado)
                st.success("Armazém restaurado com sucesso!")
                st.rerun()
            else:
                st.error("Arquivo de backup inválido.")
        except Exception as e:
            st.error(f"Erro ao restaurar backup: {e}")

st.sidebar.divider()
st.sidebar.markdown("### Alocação Manual")
col_rua, col_pos = st.sidebar.columns(2)
rua_selecionada = col_rua.selectbox("Rua", ["A", "B", "C"])

posicoes_disponiveis = sorted(df[df["rua"] == rua_selecionada]["pos_num"].unique())
pos_selecionada = col_pos.selectbox("Posição", posicoes_disponiveis)

nivel_selecionado = st.sidebar.selectbox("Nível", [10, 20, 30])

id_alvo = f"R-{rua_selecionada}-{pos_selecionada}-{nivel_selecionado}"
idx_linha = df[df["id"] == id_alvo].index[0]
linha_atual = df.loc[idx_linha]

st.sidebar.divider()
st.sidebar.subheader(f"Endereço: {id_alvo}")
if linha_atual["zona"] == "Tratativa":
    st.sidebar.error("🚨 ÁREA DE TRATATIVA")
elif linha_atual["zona"] == "Duracell":
    st.sidebar.warning("🟧 SETOR DURACELL")
else:
    st.sidebar.success("✅ ARMAZÉM GERAL")

with st.sidebar.form("form_alocacao"):
    novo_status = st.radio("Status:", ["Vazio", "Ocupado"], index=0 if linha_atual["status"] == "Vazio" else 1)
    nova_etiqueta = st.text_input("Etiqueta Unitizadora:", value=linha_atual["etiqueta"], placeholder="Ex: PAL-1234")
    nova_nf = st.text_input("Nota Fiscal (NF):", value=linha_atual["nf"], placeholder="Ex: 580333")
    novo_remetente = st.text_input("Remetente:", value=linha_atual["remetente"], placeholder="Nome do Cliente")
    novos_volumes = st.number_input("Volumes:", value=int(linha_atual["volumes"]), min_value=0, step=1)
    
    salvar = st.form_submit_button("💾 Salvar Alteração", use_container_width=True)
    
    if salvar:
        st.session_state.estoque.at[idx_linha, "status"] = novo_status
        if novo_status == "Vazio":
            st.session_state.estoque.at[idx_linha, "etiqueta"] = ""
            st.session_state.estoque.at[idx_linha, "nf"] = ""
            st.session_state.estoque.at[idx_linha, "remetente"] = ""
            st.session_state.estoque.at[idx_linha, "volumes"] = 0
        else:
            st.session_state.estoque.at[idx_linha, "etiqueta"] = nova_etiqueta
            st.session_state.estoque.at[idx_linha, "nf"] = nova_nf
            st.session_state.estoque.at[idx_linha, "remetente"] = novo_remetente
            st.session_state.estoque.at[idx_linha, "volumes"] = novos_volumes
        
        salvar_estoque(st.session_state.estoque)
        st.rerun()

# ---------------------------------------------------------
# 4. VISUALIZAÇÃO 3D REALISTA 
# ---------------------------------------------------------
dados_json = json.dumps(st.session_state.estoque.to_dict(orient="records"))

html_3d = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ margin: 0; background: #f3f4f6; color: #111827; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; overflow: hidden; }}
        #container3d {{ width: 100%; height: 580px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        
        #tooltip {{
            position: absolute; background: rgba(255, 255, 255, 0.95); border: 1px solid #e5e7eb;
            padding: 12px 16px; border-radius: 8px; display: none; pointer-events: none;
            font-size: 13px; z-index: 10; box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            backdrop-filter: blur(8px); color: #1f2937; max-width: 300px;
        }}
        
        #legend {{
            position: absolute; bottom: 15px; left: 15px; background: rgba(255, 255, 255, 0.9);
            border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 14px; font-size: 11px;
            display: flex; gap: 12px; align-items: center; backdrop-filter: blur(4px);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); color: #374151; font-weight: 500;
        }}
        
        .legend-item {{ display: flex; align-items: center; gap: 5px; }}
        .legend-color {{ width: 12px; height: 12px; border-radius: 3px; }}
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div id="container3d"></div>
    <div id="tooltip"></div>
    <div id="legend">
        <div class="legend-item"><div class="legend-color" style="background:#10b981; opacity:0.3; border:1px solid #10b981;"></div> Livre</div>
        <div class="legend-item"><div class="legend-color" style="background:#f59e0b;"></div> Duracell</div>
        <div class="legend-item"><div class="legend-color" style="background:#3b82f6;"></div> Ocupado Geral</div>
        <div class="legend-item"><div class="legend-color" style="background:#e11d48;"></div> Tratativa</div>
    </div>

    <script>
        const dados = {dados_json};
        
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf3f4f6);
        scene.fog = new THREE.FogExp2(0xf3f4f6, 0.008);

        const camera = new THREE.PerspectiveCamera(45, window.innerWidth / 580, 0.1, 1000);
        camera.position.set(15, 25, 42);

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: false }});
        renderer.setSize(window.innerWidth, 580);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        document.getElementById('container3d').appendChild(renderer.domElement);

        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.target.set(15, 3, -3);
        controls.maxPolarAngle = Math.PI / 2 - 0.02;

        scene.add(new THREE.AmbientLight(0xffffff, 0.75));
        
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.6);
        dirLight.position.set(35, 45, 25);
        dirLight.castShadow = true;
        dirLight.shadow.mapSize.width = 2048;
        dirLight.shadow.mapSize.height = 2048;
        dirLight.shadow.bias = -0.0005;
        scene.add(dirLight);

        const fillLight = new THREE.DirectionalLight(0xe0e7ff, 0.4);
        fillLight.position.set(-30, 20, -20);
        scene.add(fillLight);

        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const context = canvas.getContext('2d');
        context.fillStyle = '#e5e7eb';
        context.fillRect(0, 0, 128, 128);
        context.fillStyle = '#d1d5db';
        context.fillRect(0, 0, 64, 64);
        context.fillRect(64, 64, 64, 64);
        
        const floorTexture = new THREE.CanvasTexture(canvas);
        floorTexture.wrapS = THREE.RepeatWrapping;
        floorTexture.wrapT = THREE.RepeatWrapping;
        floorTexture.repeat.set(40, 25);

        const floorGeo = new THREE.PlaneGeometry(140, 90);
        const floorMat = new THREE.MeshStandardMaterial({{ map: floorTexture, roughness: 0.8, metalness: 0.05 }});
        const floor = new THREE.Mesh(floorGeo, floorMat);
        floor.rotation.x = -Math.PI / 2;
        floor.position.y = -0.05;
        floor.receiveShadow = true;
        scene.add(floor);

        const grid = new THREE.GridHelper(140, 70, 0x9ca3af, 0xe5e7eb);
        grid.position.y = -0.04;
        scene.add(grid);

        const matMontanteGeral = new THREE.MeshStandardMaterial({{ color: 0x1e3a8a, metalness: 0.6, roughness: 0.3 }});
        const matMontanteTrat = new THREE.MeshStandardMaterial({{ color: 0x991b1b, metalness: 0.6, roughness: 0.3 }});
        const matLongarina = new THREE.MeshStandardMaterial({{ color: 0xd97706, metalness: 0.5, roughness: 0.4 }});
        const matPaleteMadeira = new THREE.MeshStandardMaterial({{ color: 0x854d0e, roughness: 0.85 }});
        
        const matOcupadoGeral = new THREE.MeshStandardMaterial({{ color: 0x3b82f6, roughness: 0.4, metalness: 0.1 }});
        const matOcupadoTrat = new THREE.MeshStandardMaterial({{ color: 0xe11d48, roughness: 0.3, metalness: 0.2 }});
        const matOcupadoDuracell = new THREE.MeshStandardMaterial({{ color: 0xf59e0b, roughness: 0.3, metalness: 0.2 }});
        
        const matVazioGeral = new THREE.MeshBasicMaterial({{ color: 0x10b981, wireframe: true, transparent: true, opacity: 0.2 }});
        const matVazioTrat = new THREE.MeshBasicMaterial({{ color: 0xe11d48, wireframe: true, transparent: true, opacity: 0.3 }});
        const matVazioDuracell = new THREE.MeshBasicMaterial({{ color: 0xf59e0b, wireframe: true, transparent: true, opacity: 0.3 }});

        const boxGeo = new THREE.BoxGeometry(1.05, 0.8, 1.1);
        const palletGeo = new THREE.BoxGeometry(1.15, 0.1, 1.18);
        const colGeo = new THREE.BoxGeometry(0.08, 4.8, 0.08);
        const beamGeoLong = new THREE.BoxGeometry(2.55, 0.08, 0.06); 
        const beamGeoCross = new THREE.BoxGeometry(0.06, 0.06, 1.3);

        const objetosInterativos = [];
        const racksCriados = new Set();

        dados.forEach(item => {{
            let rackX = 40 - (item.col_idx * 2.8);
            let posZ = item.z_pos;
            let rackKey = `${{item.rua}}_${{item.col_idx}}_${{item.z_pos}}`; 

            if (!racksCriados.has(rackKey)) {{
                racksCriados.add(rackKey);
                const rackGroup = new THREE.Group();
                let matColuna = item.zona === "Tratativa" ? matMontanteTrat : matMontanteGeral;

                const offsetsX = [-1.28, 1.28];
                const offsetsZ = [-0.6, 0.6];

                offsetsX.forEach(ox => {{
                    offsetsZ.forEach(oz => {{
                        const colMesh = new THREE.Mesh(colGeo, matColuna);
                        colMesh.position.set(rackX + ox, 2.35, posZ + oz);
                        colMesh.castShadow = true;
                        colMesh.receiveShadow = true;
                        rackGroup.add(colMesh);
                    }});
                }});

                const niveisY = [0.25, 1.65, 3.05];
                niveisY.forEach(ny => {{
                    [-0.6, 0.6].forEach(oz => {{
                        const beam = new THREE.Mesh(beamGeoLong, matLongarina);
                        beam.position.set(rackX, ny, posZ + oz);
                        beam.castShadow = true;
                        rackGroup.add(beam);
                    }});

                    [-1.28, 1.28].forEach(ox => {{
                        const crossBeam = new THREE.Mesh(beamGeoCross, matColuna);
                        crossBeam.position.set(rackX + ox, ny - 0.02, posZ);
                        rackGroup.add(crossBeam);
                    }});
                }});
                scene.add(rackGroup);
            }}

            let posX = (item.side === 'left') ? rackX - 0.62 : rackX + 0.62;
            let posY = (item.nivel / 10) * 1.4 - 0.55;

            const group = new THREE.Group();
            group.position.set(posX, posY, posZ);

            if (item.status === "Ocupado") {{
                const palletMesh = new THREE.Mesh(palletGeo, matPaleteMadeira);
                palletMesh.position.y = -0.4;
                palletMesh.castShadow = true;
                palletMesh.receiveShadow = true;
                group.add(palletMesh);

                let matBox = matOcupadoGeral;
                if (item.zona === "Tratativa") matBox = matOcupadoTrat;
                else if (item.zona === "Duracell") matBox = matOcupadoDuracell;

                const boxMesh = new THREE.Mesh(boxGeo, matBox);
                boxMesh.castShadow = true;
                boxMesh.receiveShadow = true;
                boxMesh.userData = item;
                group.add(boxMesh);
                objetosInterativos.push(boxMesh);
            }} else {{
                let matEmpty = matVazioGeral;
                if (item.zona === "Tratativa") matEmpty = matVazioTrat;
                else if (item.zona === "Duracell") matEmpty = matVazioDuracell;

                const emptyMesh = new THREE.Mesh(boxGeo, matEmpty);
                emptyMesh.userData = item;
                group.add(emptyMesh);
                objetosInterativos.push(emptyMesh);
            }}
            scene.add(group);
        }});

        const raycaster = new THREE.Raycaster();
        const mouse = new THREE.Vector2();
        const tooltip = document.getElementById('tooltip');

        window.addEventListener('mousemove', (event) => {{
            const rect = renderer.domElement.getBoundingClientRect();
            mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

            raycaster.setFromCamera(mouse, camera);
            const intersects = raycaster.intersectObjects(objetosInterativos);

            if (intersects.length > 0) {{
                const target = intersects[0].object;
                const d = target.userData;

                document.body.style.cursor = 'pointer';
                tooltip.style.display = 'block';
                tooltip.style.left = (event.clientX + 16) + 'px';
                tooltip.style.top = (event.clientY + 16) + 'px';

                let tagZona = '<div style="color:#2563eb; font-weight:bold; margin-bottom:4px; font-size:11px; letter-spacing:1px;">📦 ARMAZÉM GERAL</div>';
                if (d.zona === 'Tratativa') {{
                    tagZona = '<div style="color:#e11d48; font-weight:bold; margin-bottom:4px; font-size:11px; letter-spacing:1px;">🚨 ZONA DE TRATATIVA</div>';
                }} else if (d.zona === 'Duracell') {{
                    tagZona = '<div style="color:#d97706; font-weight:bold; margin-bottom:4px; font-size:11px; letter-spacing:1px;">🟧 SETOR DURACELL</div>';
                }}

                let statusBadge = d.status === 'Ocupado'
                    ? '<span style="background:#fef3c7; color:#b45309; border:1px solid #fcd34d; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">OCUPADO</span>'
                    : '<span style="background:#d1fae5; color:#047857; border:1px solid #6ee7b7; padding:2px 6px; border-radius:4px; font-weight:bold; font-size:11px;">DISPONÍVEL</span>';

                tooltip.innerHTML = `
                    ${{tagZona}}
                    <div style="font-size:15px; font-weight:bold; margin-bottom:6px; color:#111827;">Endereço: ${{d.id}}</div>
                    <div style="margin-bottom:4px;">Status: ${{statusBadge}}</div>
                    <div style="color:#4b5563; font-size:12px; margin-top:6px; background:#f3f4f6; padding:6px; border-radius:4px;">
                        Nota(s) Fiscal(is): <span style="color:#111827; font-weight:500;">${{d.nf || '---'}}</span><br/>
                        Remetente(s): <span style="color:#111827; font-weight:500;">${{d.remetente || '---'}}</span><br/>
                        Total Volumes: <span style="color:#111827; font-weight:500;">${{d.volumes || 0}} un</span><br/>
                        Etiqueta: <span style="color:#111827; font-weight:500;">${{d.etiqueta || '---'}}</span>
                    </div>
                `;
            }} else {{
                document.body.style.cursor = 'default';
                tooltip.style.display = 'none';
            }}
        }});

        function animate() {{
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }}
        animate();

        window.addEventListener('resize', () => {{
            camera.aspect = window.innerWidth / 580;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, 580);
        }});
    </script>
</body>
</html>
"""
components.html(html_3d, height=600)

# ---------------------------------------------------------
# 5. TABELA DE CONSULTA ATUALIZADA
# ---------------------------------------------------------
st.subheader("📋 Paletes Alocados")
col_filtro, _ = st.columns([2, 2])
filtro_zona = col_filtro.radio("Filtrar por Setor/Zona:", ["Todas", "Armazém", "Duracell", "Tratativa"], horizontal=True)

df_exibir = df[df["status"] == "Ocupado"]
if filtro_zona != "Todas":
    df_exibir = df_exibir[df_exibir["zona"] == filtro_zona]

if df_exibir.empty:
    st.info("Nenhum palete alocado para o filtro selecionado.")
else:
    st.dataframe(df_exibir[["id", "rua", "pos_num", "nivel", "zona", "remetente", "nf", "volumes", "etiqueta"]], use_container_width=True)