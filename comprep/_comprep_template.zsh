function _{command}() {{
    comprep=( ${{(@f)"$({comp_func})"}} )
    while [ $#comprep -gt 0 ]; do
        num=$comprep[1]; shift comprep
        params=( ${{comprep[@]:0:$num}} ); shift $num comprep
        args=()
        choices=( "--" )
        while [ $#params -gt 0 ]; do
            ty=$params[1]; shift params
            n=$params[1]; shift params
            p=( ${{params[@]:0:$n}} ); shift $n params
            case "$ty" in
                choices)
                    choices+=( $p )
                ;;
                    description)
                    desc=( $p )
                    args+=( "-d" "desc" )
                ;;
                title)
                    args+=( "-V" $p )
                    args+=( "-X" $p )
                ;;
                prefix)
                    args+=( "-P" $p )
                ;;
                suffix)
                    args+=( "-S" $p )
                ;;
                files)
                    args+=( "-f" )
                ;;
                oneline)
                    args+=( "-l" )
                ;;
            esac
        done
        compadd $args $choices
    done
}}

compdef _{command} {command}
