 $("#login-button").click(function(event){
    event.preventDefault();
    
    //var formData = $("#loginForm").serialize();
    var $form = $("#loginForm");
    var formData = $form.form2Dic();

    $.postForm("/login",formData,function(response){

        $form.fadeOut(500);
        $('.wrapper').addClass('form-success');
    })
});

$("#create-button").click(function(event){
    event.preventDefault();

    var $form = $("#createUserForm");
    var formData = $form.form2Dic();
    $.postForm("/new",formData,function(response){

        if ( response == "redirect"){
            $form.fadeOut(500);
            $('.wrapper').addClass('form-success');
            window.setTimeout(window.location.href="/",500); 
        }
    });
});

jQuery.postForm = function(url,formData,callback){
    $.ajax({
        type:"POST",
        url:url,
        dataType:"text",
        data:$.param(formData),
        success:function(response){
            if(callback){
                callback(response);
            }
        },
        error:function(error){
            console.log("Error:",error);
        }
    });
};

jQuery.fn.form2Dic = function(){
    var fields = this.serializeArray();
    var json={};
    for (var i=0;i<fields.length;i++){
        json[fields[i].name] = fields[i].value;
    }
    if(json.next) delete json.next;
    return json;
}

//check if email is corrected while typing email address.
function checkEmail(){
    $("#emailHelp").addClass("hidden"); 
    var $email = $("input[name=email]");

    if ( $email.val()=="" || 
        !validateForm.validateEmail($email.val())){
        $("#emailHelp").removeClass("hidden"); 
    }
    else{
        $("#emailHelp").addClass("hidden"); 
    }
}

function checkName(){
    $("#nameHelp").addClass("hidden"); 
    var $newName = $("#newName");

    if ( $newName.val()=="" || 
        !validateForm.validateName($newName.val())){
        $("#nameHelp").removeClass("hidden"); 
    }
    else{
        $("#nameHelp").addClass("hidden"); 
    }
}

//obejct for validating form value.
var validateForm = {
    validateName:function(name){
        var re = /^[0-9a-zA-Z_.-]\w{4,20}$/; 
        return re.test(name);
    },

    validateEmail:function(email){
        var re = /^([\w-]+(?:\.[\w-]+)*)@((?:[\w-]+\.)*\w[\w-]{0,66})\.([a-z]{2,6}(?:\.[a-z]{2})?)$/i;
        return re.test(email);
    },

    validatePassword:function(password){
        var re = /^(?=.*\d)(?=.*[A-Z])(?=.*[a-z]).{6,20}$/; 
    }
}
