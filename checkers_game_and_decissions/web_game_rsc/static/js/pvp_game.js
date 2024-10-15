var initial_update = true;
var waiting_for_opponent = true;
var after_move_refresh =false;

var my_color;

var game_board;

var points;

var game_status;

var winner;

var options;

var turn_of;

var opponent_name;

var current_seq = [];


function draw_circle(ctx, x, y, radius, fill, stroke, strokeWidth) {
    ctx.beginPath()
    ctx.arc(x, y, radius, 0, 2 * Math.PI, false)
    if (fill) {
      ctx.fillStyle = fill
      ctx.fill()
    }
    if (stroke) {
      ctx.lineWidth = strokeWidth
      ctx.strokeStyle = stroke
      ctx.stroke()
    }
  }


function draw_plain_checkerboard(canvas){
    var ctx = canvas.getContext("2d");

    var is_dark = false
    for(var x=0; x<8; x++){
        for(var y=0; y<8; y++){
            if (is_dark){
                ctx.fillStyle = "#501900";
                //ctx.fillStyle = "#000000";
            }else{
                ctx.fillStyle = "#ffe1b4";
                //ctx.fillStyle = "#ffffff";
            }

            ctx.fillRect(x*75,y*75,x*75+75,x*75+75);

            is_dark = !is_dark
        }
        is_dark = !is_dark
    }
}

function draw_game_state(canvas){
    draw_plain_checkerboard(canvas);

    var player_perspective_game_state = [];

    if(my_color=='RED'){
        //Rotate game_state 180 degrees
        for(var x = 7; x>= 0; x--){
            var new_col = [];
            for(var y = 7; y>= 0; y--){
                new_col[7-y] = game_board[x][y]
            }
            player_perspective_game_state.push(new_col);
        }
    }else
        player_perspective_game_state = game_board;


    var ctx = canvas.getContext("2d");
    for (var x = 0; x<8; x++)
        for (var y = 0; y<8; y++){
            if (player_perspective_game_state[x][y] == -1){
                draw_circle(ctx, (x*75+37), (y*75+37), 30, 'green','green',5);
            }
            if (player_perspective_game_state[x][y] == -2){
                draw_circle(ctx, (x*75+37), (y*75+37), 30, 'green','white',5);
            }
            if (player_perspective_game_state[x][y] == 1){
                draw_circle(ctx, (x*75+37), (y*75+37), 30, 'red','red',5);
            }
            if (player_perspective_game_state[x][y] == 2){
                draw_circle(ctx, (x*75+37), (y*75+37), 30, 'red','white',5);
            }
        }
}


function draw_seq(canvas){
    var ctx = canvas.getContext("2d");

    if(current_seq.length > 0){
        //ctx.beginPath();
        xy = determine_xy_from_id(current_seq[0]);
        if (my_color == 'RED'){
            xy[0] = 7-xy[0];
            xy[1] = 7-xy[1];
        }
        //ctx.moveTo(xy[0]*75+37, xy[1]*75+37);
        for(var i=0; i<current_seq.length; i++){
            if(i > 0){
                xy_old = determine_xy_from_id(Math.abs(current_seq[i-1]));
                if (my_color == 'RED'){
                    xy_old[0] = 7-xy_old[0];
                    xy_old[1] = 7-xy_old[1];
                }
                xy = determine_xy_from_id(Math.abs(current_seq[i]));
                if (my_color == 'RED'){
                    xy[0] = 7-xy[0];
                    xy[1] = 7-xy[1];
                }
                ctx.beginPath();
                ctx.moveTo(xy_old[0]*75+37, xy_old[1]*75+37);
                ctx.lineWidth = 5;
                ctx.strokeStyle = 'white';
                ctx.lineTo(xy[0]*75+37, xy[1]*75+37);
                ctx.stroke();
            }
            if(current_seq[i] > 0){
                draw_circle(ctx, (xy[0]*75+37), (xy[1]*75+37), 5, 'white','white',1);
            }else{
                draw_circle(ctx, (xy[0]*75+37), (xy[1]*75+37), 5, 'blue','blue',1);
            }
        }
    }

}


function determine_click_xy(x,y){
    x_res = Math.floor(x/75.0);
    y_res = Math.floor(y/75.0);

    return [x_res,y_res];
}


function determine_id_from_xy(x,y){
    
    id = y * 4 + 1;

    if (y%2 ==1){
        id += x/2.0;
    }else{
        id += (x-1)/2.0;
    }

    if (id == Math.floor(id)){
        return Math.floor(id);
    }

    return null;
}

function is_subsequence_legal(subseq){
    subseq_len = subseq.length;
    for(var i = 0; i < options.length; i++){
        if(options[i].length >= subseq_len){
            var check = true;
            for(var j = 0; j<subseq_len; j++){
                if(subseq[j] != options[i][j]){
                    check = false;
                }
            }
            if (check){
                return true;
            }
        }
    }

    return false;
}


function is_full_sequence_legal(seq){
    seq_len = seq.length;
    for(var i =0; i<options.length; i++){
        if(options[i].length == seq_len){
            var check = true;
            for(var j = 0; j<seq_len; j++){
                if(seq[j] != options[i][j]){
                    check = false;
                }
            }
            if (check){
                return true;
            }
        }
    }

    return false;
}


function determine_xy_from_id(id){

    y = Math.floor((id-1)/4.0);

    x = ((id-1)%4)*2

    if (y%2 == 0){
        x += 1;
    }

    return [x,y];

}


function request_perform_move(game_id, user_uuid, seq){
    var json_txt= '{"game_id": '+game_id+', "user_uuid": "'+user_uuid+'", "move": ['+seq.join(',')+']}';
    //const json = JSON.parse(json_txt);

    const req_move = async (json) => {
        const response = await fetch('/move', {
            method: 'POST',
            body: json, // string or object
            headers: {
                'Content-Type': 'application/json'
            }
        });
        current_seq = [];
        after_move_refresh = true;
        request_game_status(game_id, user_uuid);
    }

    req_move(json_txt);
}


function handle_click(x_coor,y_coor){
    if (my_color == turn_of && game_status == 'IN_PROGRESS' && !waiting_for_opponent){
        var xy = determine_click_xy(x_coor,y_coor);
        var x = xy[0];
        var y = xy[1];
        if (my_color == 'RED'){
            x = 7-x;
            y = 7-y;
        }
        var id = determine_id_from_xy(x,y);
        
        
        if (id == null){
            current_seq = [];
            draw_game_state(canvas);
        }

        if (current_seq.length == 0){
            current_seq.push(id);
            if( !is_subsequence_legal(current_seq)){
                current_seq = [];
                draw_game_state(canvas);
            }else{
                draw_seq(canvas);
            }
        }else{
            xy_old = determine_xy_from_id(current_seq[current_seq.length-1]);
            
            if (Math.abs(x-xy_old[0]) == Math.abs(y-xy_old[1])){
                if(Math.abs(x-xy_old[0]) == 1){
                    current_seq.push(id);
                    if( !is_subsequence_legal(current_seq)){
                        current_seq = [];
                        draw_game_state(canvas);
                    }else{
                        draw_seq(canvas);
                    }
                }else{
                    for(var i =0; i<Math.abs(x-xy_old[0])-1;i++){
                        x_checked = xy_old[0] + (i+1)*(x-xy_old[0])/Math.abs(x-xy_old[0])
                        y_checked = xy_old[1] + (i+1)*(y-xy_old[1])/Math.abs(y-xy_old[1])
                        if ((game_board[x_checked][y_checked] < 0 && my_color == 'RED') || (game_board[x_checked][y_checked] > 0 && my_color == 'GREEN')){
                            current_seq.push(-determine_id_from_xy(x_checked, y_checked));
                            break;
                        }
                    }
                    current_seq.push(id);
                    if( !is_subsequence_legal(current_seq)){
                        current_seq = [];
                        draw_game_state(canvas);
                    }else{
                        draw_seq(canvas);
                    }
                }
            }else{
                current_seq = [];
                draw_game_state(canvas);
            }
        }

        if(is_full_sequence_legal(current_seq)){
            request_perform_move(game_id, user_uuid, current_seq);
        }
    }
}

function update_game_status(game_status_resp){
    const game_status_parsed = JSON.parse(game_status_resp);

    my_color = game_status_parsed.my_color;
    
    var game_board_new = game_status_parsed.game_board;
    if(game_board_new != game_board){
        game_board = game_board_new;
        current_seq = [];
        draw_game_state(canvas);
    }

    points = game_status_parsed.points;
    // TODO in the future if I want to present it

    game_status = game_status_parsed.status;
    winner = game_status_parsed.winner;
    game_status_html = document.getElementById("game_status");
    if (game_status == "IN_PROGRESS")
        game_status_html.innerHTML = "Game is in progress";
    if (game_status == "DRAW")
        game_status_html.innerHTML = "DRAW :)";
    if (game_status == "WON")
        if (winner == my_color)
            game_status_html.innerHTML = "YOU WON :D";
        else
            game_status_html.innerHTML = "YOU LOST :C";

    options = game_status_parsed.options;

    turn_of = game_status_parsed.turn_of;
    turn_of_html = document.getElementById("turn_of")
    if(turn_of == ''){
        turn_of_html.outerHTML = '<form method="get" action="/"><input type="submit" value="BACK TO MENU"></form>'
    }else{
        if (turn_of == my_color){
            if (my_color == 'GREEN')
                turn_of_html.outerHTML = '<p id="turn_of" style="color:GREEN">YOUR TURN</p>'
            else
                turn_of_html.outerHTML = '<p id="turn_of" style="color:RED">YOUR TURN</p>'
        }else{
            if (my_color == 'GREEN')
                turn_of_html.outerHTML = '<p id="turn_of" style="color:RED">OPPONENT\'S TURN</p>'
            else
                turn_of_html.outerHTML = '<p id="turn_of" style="color:GREEN">OPPONENT\'S TURN</p>'
        }
    }

    opponent_name = game_status_parsed.opponent_name;
    if (opponent_name != null && opponent_name != ""){
        opponent_html = document.getElementById("opponent_name");
        opponent_html.innerHTML = "Your opponent is "+opponent_name.toUpperCase();
        waiting_for_opponent = false;
    }
    
}

function request_game_status(game_id, user_uuid){

    const game_status_req = async (game_id, user_uuid) => {
        const response = await fetch('/game_status?game_id='+game_id+'&user_uuid='+user_uuid);
        const json = await response.text(); //extract JSON from the http response
        update_game_status(json);
    }
    if ((turn_of != my_color && turn_of != '') || initial_update || waiting_for_opponent || after_move_refresh){
        game_status_req(game_id, user_uuid);
        initial_update = false;
        after_move_refresh = false;
    }
}


// runs on page restart
var canvas = document.getElementById("checker_canvas");

draw_plain_checkerboard(canvas);

canvas.addEventListener('click', function(event) { 
    var elemLeft = canvas.offsetLeft + canvas.clientLeft
    var elemTop = canvas.offsetTop + canvas.clientTop
    var x = event.pageX - elemLeft
    var y = event.pageY - elemTop
    handle_click(x,y);
}, false);

var user_uuid = document.getElementById("user_uuid").textContent;
var game_id = document.getElementById("game_id").textContent;

request_game_status(game_id, user_uuid)
setInterval(function(){ 
    request_game_status(game_id, user_uuid) ;   
}, 2000);
