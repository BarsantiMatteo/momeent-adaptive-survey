const inputs  = document.getElementsByTagName("input")
for (let i = 0; i < inputs.length - 1; i++) {
    inputs[i].required = true;
}