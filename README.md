# otptool
### A handy GUI utility that creates, merges and reads otp area on your Flipper Zero, you can edit the name, screen model, region and timestamp of your otp.

<img width="625" height="535" alt="image" src="https://github.com/user-attachments/assets/14eef4a8-1473-481b-bec5-f068bcd79835" />


> [!WARNING]
> The program cannot overwrite an already written OTP area; it can only read it!
> The program also does not write to the OTP area; it only generates and merges OTP files into one.
> You must flash this file yourself.


Before running, install the required libraries:

```bash
pip install -R requirements.txt
```

then run the `main.py` file:

```bash
python3 main.py
```
