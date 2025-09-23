import os
import matplotlib
matplotlib.use('Agg')  # Usar backend não interativo
import matplotlib.pyplot as plt
import numpy as np

# Criar um gráfico simples
plt.figure(figsize=(10, 6))
x = np.linspace(0, 10, 100)
y = np.sin(x)
plt.plot(x, y)
plt.title('Teste de Geração de Gráfico')
plt.xlabel('X')
plt.ylabel('Y')

# Salvar como PNG
output_path = 'teste_grafico.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
plt.close()

print(f'Gráfico salvo em: {output_path}')
