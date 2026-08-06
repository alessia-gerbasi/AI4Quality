# Run CTQ on all data
cd /data/alessia.gerbasi/AI4Quality && python _02_QualityCheck/main.py --output-dir _02_QualityCheck/OUTPUTS

# Run CTQ on subset
cd /data/alessia.gerbasi/AI4Quality && python _02_QualityCheck/main.py --max-cases 20 --output-dir _02_QualityCheck/OUTPUTS_test20

# Run Dashboard
cd /data/alessia.gerbasi/AI4Quality && /data/alessia.gerbasi/miniconda3/envs/ctq/bin/python -m streamlit run _02_QualityCheck/dashboard.py --server.headless true --server.port 8505