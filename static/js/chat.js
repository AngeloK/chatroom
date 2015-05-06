//js for chatroom

$(document).ready(function(){
    // post message if user click "submit"

    $("#messageForm").on("submit",function(){
        $this = $(this);
        var formData = $this.serialize(); 
        newMessage(formData);
        $(".messageBox").animate({ scrollTop: $(document).height() }, "slow"); 
        $("#message").val("").select();
        return false;
    });
    //post message if user enter "Enter"
    $("#messageForm").on("keypress",function(e){
        if ( e.keyCode == 13 ) {
            $this = $(this);
            //serializde formdata
            var formData = $this.serialize(); 
            newMessage(formData);
            $(".messageBox").animate({ scrollTop: $(document).height() }, 
                                     "slow"); 
            $("#message").val("").select();
            return false;
        }
    });

    $(".messageBox").animate({ scrollTop: $(document).height() }, "slow"); 

    cookieValue = $.cookie("chat_user");

    if (cookieValue) console.log(cookieValue);

    //focus on input area
    $("#message").select();

    //long polling
    updater.poll();
})

function newMessage(formData){
    // post form data to server by ajax.
    $.ajax({
        type:"POST",
        url:"message/new",
        dataType:"text",
        data:formData,
    });
}

//long polling object.
var updater = {
    errorSleepTime: 500,
    cursor: null,

    poll: function(){
        var args = {"_xsrf":$.cookie("_xsrf")};
        if ( updater.cursor ) {
            args.cursor = updater.cursor;
        }
        $.ajax({
            type:"POST",
            url:"message/update",
            dataType:"text",
            data:$.param(args),
            success:updater.onSuccess,
            error:updater.onError
        });  
    },

    onSuccess: function(response){
        updater.errorSleepTime = 500;
        updater.newMessage(response);
        window.setTimeout(updater.poll, 0);
    },

    onError: function(){
        updater.errorSleepTime *= 2;
        console.log("Polling error,wait for "+updater.errorSleepTime);
        window.setTimeout(updater.poll,updater.errorSleepTime);
    },

    newMessage: function(response){
        var messages = eval("("+response+")").messages
        if ( !messages ) {
            return;
        }
        len = messages.length;
        updater.cursor = messages[len-1].id
        for(var i=0;i<len;i++){
            updater.showMessage(messages[i]);
        }

    },

    showMessage: function(message){
        var $msgLi = $("<li>");
        var $msgDiv = $("<div>",{
            id:message.id,
            class:"msgContent",
            text:message.user_name+": "+message.body
        });
        $msgLi.append($msgDiv);
        $(".messageBox ul").append($msgLi);
    },

}




