import torch
import time

# デバイス選択
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print("Using device:", device)

# 10000 x 10000 のランダムな行列を作ってGPUで計算
a = torch.randn(10000, 10000, device=device)
b = torch.randn(10000, 10000, device=device)

start = time.time()
c = torch.matmul(a, b)
end = time.time()

print(f"Matrix multiplication done in {end - start:.2f} seconds.")
