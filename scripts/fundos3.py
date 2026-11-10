import sys, json
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]
W,H = 1280,720
S = 2  # supersample
BG="#0E1117"; CARD="#171B24"; BORDER="#262C38"; RED="#E5484D"; GOLD="#F5B841"; TXT="#F3F4F6"; SUB="#8B93A1"
F = lambda w,s: ImageFont.truetype(f"/usr/share/fonts/opentype/inter/Inter-{w}.otf", s*S)

kpi_x=[24,273,522,771,1020]; kpi_w=236
filtros=[(24,74,236,52),(273,74,236,52),(522,74,236,52)]
periodo=(771,74,485,52)
ROTULOS=["LOJA","CATEGORIA","MÊS","PERÍODO ANALISADO"]
pages = {
 "fundo_1_visao_geral.png": ("Visão Geral", "Receita, volume e desempenho das lojas", [
   ("line",24,252,760,220),("c",800,252,456,220),
   ("c",24,488,610,208),("c",650,488,606,208)]),
 "fundo_2_filmes_atores.png": ("Filmes e Atores", "Catálogo, títulos de destaque e elenco", [
   ("c",24,252,600,444),("c",640,252,616,214),
   ("c",640,482,300,214),("c",956,482,300,214)]),
 "fundo_3_clientes_operacao.png": ("Clientes e Operação", "Base de clientes, devoluções e atrasos", [
   ("c",24,252,610,220),("c",650,252,606,220),
   ("c",24,488,610,208),("c",650,488,606,208)]),
 "fundo_4_sazonalidade.png": ("Sazonalidade e Datas", "Feriados, vésperas, férias e datas comemorativas", [
   ("c",24,252,760,220),("c",800,252,456,220),
   ("c",24,488,610,208),("c",650,488,606,208)]),
 "fundo_5_estoque_retencao.png": ("Estoque e Retenção", "Ocupação das cópias e coorte de clientes (DAX avançado)", [
   ("c",24,252,760,444),("c",800,252,456,220),("c",800,488,456,208)]),
 "fundo_6_modelos.png": ("Previsões e Recomendações", "Modelos em Python: demanda, cópias ideais e risco de abandono", [
   ("c",24,252,610,220),("c",650,252,606,220),
   ("c",24,488,610,208),("c",650,488,606,208)]),
}
def rr(d,x,y,w,h,fill=CARD,outline=BORDER,r=10):
    d.rounded_rectangle([x*S,y*S,(x+w)*S,(y+h)*S], r*S, fill=fill, outline=outline, width=1*S)
for fn,(title,sub,blocks) in pages.items():
    im=Image.new("RGB",(W*S,H*S),BG); d=ImageDraw.Draw(im)
    # header
    d.rectangle([0,0,W*S,64*S], fill="#11151D"); d.line([0,64*S,W*S,64*S], fill=BORDER, width=S)
    # brand mark: film strip
    x0,y0=24,18
    d.rounded_rectangle([x0*S,y0*S,(x0+28)*S,(y0+28)*S], 6*S, fill=RED)
    for i in range(3):
        d.rectangle([(x0+5)*S,(y0+5+i*7)*S,(x0+9)*S,(y0+8+i*7)*S], fill="#11151D")
        d.rectangle([(x0+19)*S,(y0+5+i*7)*S,(x0+23)*S,(y0+8+i*7)*S], fill="#11151D")
    d.text((62*S,17*S),"REBOBINA",font=F("Bold",15),fill=TXT)
    d.text((62*S,36*S),"LOCADORA ANALYTICS",font=F("Medium",9),fill=GOLD)
    d.line([218*S,16*S,218*S,48*S], fill=BORDER, width=S)
    d.text((236*S,13*S),title,font=F("SemiBold",19),fill=TXT)
    d.text((236*S,39*S),sub,font=F("Regular",11),fill=SUB)
    # a linha de filtros não é desenhada aqui: cada filtro é um visual com moldura própria
    # KPI cards with accent
    for x in kpi_x:
        rr(d,x,136,kpi_w,100)
        d.rounded_rectangle([x*S,(136+18)*S,(x+4)*S,(136+82)*S], 2*S, fill=RED)
    for b in blocks: rr(d,*b[1:])
    # footer
    d.text((24*S,702*S),"Fonte: Locadora Rebobina (base fictícia) · títulos e bilheterias reais do TMDB 5000 · Desenvolvido por Gustavo Oliveira",font=F("Regular",9),fill="#5B6270")
    im=im.resize((W,H),Image.LANCZOS); im.save(f"{out}/{fn}")
print("ok")
