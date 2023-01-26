window.addEventListener("load", function(){
    var password = document.getElementById("password");
    var confirmPassword = document.getElementById("confirm");
    var errorMessage = document.getElementById("error_message");
    var form = document.getElementById("form");
  
    form.addEventListener("submit", function(event){
    if(password.value != confirmPassword.value){
        event.preventDefault();
        errorMessage.style.display = "block";
    } else {
        errorMessage.style.display = "none";
    }
  });

    confirmPassword.addEventListener("blur", function(){
    if(password.value != confirmPassword.value){
        errorMessage.style.display = "block";
    } else {
        errorMessage.style.display = "none";
    }
  });
});
